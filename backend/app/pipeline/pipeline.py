"""Main processing pipeline: bubble detection → OCR → context → translate → inpaint → typeset."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Awaitable

from sqlalchemy import delete
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.page import Page
from ..models.project import Project
from ..models.translation import TranslationEntry
from ..services.bubble_detector import detect_bubbles
from ..services.context_builder import build_context
from ..services.inpainting_service import inpaint_page_image
from ..services.ocr_service import extract_bubble_texts
from ..services.translation_service import translate_batch
from ..services.typesetting_service import typeset_page

ProgressCallback = Callable[[str, int | None], Awaitable[None]] | None

_BATCH_SIZE = 20


async def _noop(stage: str, page: int | None = None) -> None:
    pass


async def process_project(project_id: str, progress_callback: ProgressCallback = None) -> None:
    """Full pipeline for a project. Updates DB in-place. Raises on fatal errors."""
    cb = progress_callback or _noop

    async with AsyncSessionLocal() as session:
        # ── Load project ────────────────────────────────────────────────────
        project = (
            await session.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id!r} not found.")

        pages = (
            await session.execute(
                select(Page)
                .where(Page.project_id == project_id)
                .order_by(Page.page_number.asc())
            )
        ).scalars().all()

        if not pages:
            project.status = "review"
            await session.commit()
            return

        # ── Reset state ──────────────────────────────────────────────────────
        page_ids = [p.id for p in pages]
        await session.execute(
            delete(TranslationEntry).where(TranslationEntry.page_id.in_(page_ids))
        )
        project.status = "processing"
        project.processed_pages = 0
        for page in pages:
            page.status = "pending"
            page.cleaned_path = None
            page.translated_path = None
            page.bubbles = None
        await session.commit()

        # ── Stage 1: Bubble detection ────────────────────────────────────────
        for page in pages:
            page.status = "detecting"
            await session.commit()
            try:
                page.bubbles = detect_bubbles(Path(page.original_path))
            except Exception as exc:
                page.bubbles = []
            await session.commit()
            await cb("bubble_detection", page.page_number)

        # ── Stage 2: OCR ────────────────────────────────────────────────────
        all_texts: list[str] = []
        for page in pages:
            page.status = "ocr"
            await session.commit()
            try:
                ocr_results = extract_bubble_texts(
                    Path(page.original_path), page.bubbles or []
                )
            except Exception:
                ocr_results = []

            for bubble in ocr_results:
                entry = TranslationEntry(
                    page_id=page.id,
                    bubble_index=bubble["bubble_index"],
                    original_text=bubble["original_text"],
                    translated_text="",
                    x=bubble["x"],
                    y=bubble["y"],
                    w=bubble["w"],
                    h=bubble["h"],
                )
                session.add(entry)
                if bubble["original_text"].strip():
                    all_texts.append(bubble["original_text"])

            await session.commit()
            await cb("ocr", page.page_number)

        # ── Stage 3: Story context ───────────────────────────────────────────
        try:
            context = await build_context(project_id, all_texts)
        except Exception:
            context = {"summary": "", "tone": "", "characters": [], "glossary": []}
        await cb("context_built", None)

        # ── Stage 4: Translation (batched) ───────────────────────────────────
        translation_entries: list[TranslationEntry] = (
            await session.execute(
                select(TranslationEntry)
                .join(Page)
                .where(Page.project_id == project_id)
                .order_by(Page.page_number.asc(), TranslationEntry.bubble_index.asc())
            )
        ).scalars().all()

        glossary = context.get("glossary", [])
        summary = context.get("summary", "")

        for batch_start in range(0, len(translation_entries), _BATCH_SIZE):
            chunk = translation_entries[batch_start: batch_start + _BATCH_SIZE]
            request_items = [
                {
                    "bubble_index": idx,
                    "text": entry.original_text,
                    "page_id": entry.page_id,
                }
                for idx, entry in enumerate(chunk)
            ]
            try:
                translated_items = await translate_batch(
                    request_items, context=summary, glossary=glossary
                )
                by_idx = {item["bubble_index"]: item["translated_text"] for item in translated_items}
            except Exception:
                by_idx = {}  # fallback: keep empty translated text

            for local_idx, entry in enumerate(chunk):
                entry.translated_text = by_idx.get(local_idx, entry.original_text)

            await session.commit()
            await cb("translation", batch_start + len(chunk))

        # ── Stage 5: Inpainting ─────────────────────────────────────────────
        for page in pages:
            page.status = "inpainting"
            await session.commit()
            try:
                cleaned = inpaint_page_image(page)
                page.cleaned_path = cleaned or page.original_path
            except Exception:
                page.cleaned_path = page.original_path
            await session.commit()
            await cb("inpainting", page.page_number)

        # ── Stage 6: Typesetting ─────────────────────────────────────────────
        # Re-fetch entries after translation updates
        translation_entries = (
            await session.execute(
                select(TranslationEntry)
                .join(Page)
                .where(Page.project_id == project_id)
                .order_by(Page.page_number.asc(), TranslationEntry.bubble_index.asc())
            )
        ).scalars().all()

        entries_by_page: dict[str, list[TranslationEntry]] = {}
        for entry in translation_entries:
            entries_by_page.setdefault(entry.page_id, []).append(entry)

        for page in pages:
            page.status = "typesetting"
            await session.commit()
            page_entries = entries_by_page.get(page.id, [])
            try:
                page.translated_path = typeset_page(page, page_entries)
                page.status = "done"
            except Exception:
                page.translated_path = page.cleaned_path or page.original_path
                page.status = "done"
            project.processed_pages += 1
            await session.commit()
            await cb("typesetting", page.page_number)

        # ── Finalise ─────────────────────────────────────────────────────────
        project.status = "review"
        project.processed_pages = len(pages)
        await session.commit()
        await cb("completed", None)
