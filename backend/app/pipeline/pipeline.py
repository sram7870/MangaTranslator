from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.project import Project
from ..models.page import Page
from ..models.translation import TranslationEntry
from ..services.bubble_detector import detect_bubbles
from ..services.ocr_service import extract_bubble_texts
from ..services.context_builder import build_context
from ..services.translation_service import translate_batch
from ..services.inpainting_service import inpaint_page_image
from ..services.typesetting_service import typeset_page

async def process_project(project_id: str, progress_callback=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        pages_result = await session.execute(select(Page).where(Page.project_id == project.id).order_by(Page.page_number.asc()))
        pages = pages_result.scalars().all()
        all_texts: list[str] = []

        await session.execute(
            delete(TranslationEntry).where(
                TranslationEntry.page_id.in_([page.id for page in pages])
            )
        )
        project.status = "processing"
        project.processed_pages = 0
        await session.commit()

        for page in pages:
            page.status = "detecting"
            page.cleaned_path = None
            page.translated_path = None
            await session.commit()
            page.bubbles = detect_bubbles(Path(page.original_path))
            page.status = "ocr"
            await session.commit()
            if progress_callback:
                await progress_callback("bubble_detection", page.page_number)

        for page in pages:
            page.status = "ocr"
            await session.commit()
            ocr_results = extract_bubble_texts(Path(page.original_path), page.bubbles or [])
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
                all_texts.append(entry.original_text)
            await session.commit()
            await session.refresh(page)
            if progress_callback:
                await progress_callback("ocr", page.page_number)

        context = await build_context(project.id, all_texts)
        if progress_callback:
            await progress_callback("context_built")

        translation_entries_result = await session.execute(select(TranslationEntry).join(Page).where(Page.project_id == project.id).order_by(Page.page_number.asc(), TranslationEntry.bubble_index.asc()))
        translation_entries = translation_entries_result.scalars().all()
        batch_size = 20
        for start in range(0, len(translation_entries), batch_size):
            chunk = translation_entries[start : start + batch_size]
            request_items = [
                {
                    "bubble_index": index,
                    "text": entry.original_text,
                    "page_id": entry.page_id,
                }
                for index, entry in enumerate(chunk)
            ]
            translated_items = await translate_batch(request_items, context=context["summary"], glossary=context.get("glossary", []))
            translated_by_index = {item["bubble_index"]: item["translated_text"] for item in translated_items}
            for index, entry in enumerate(chunk):
                entry.translated_text = translated_by_index[index]
            await session.commit()
            if progress_callback and chunk:
                await progress_callback("translation", start + len(chunk))
        await session.commit()

        for page in pages:
            page.status = "inpainting"
            await session.commit()
            cleaned = inpaint_page_image(page)
            page.cleaned_path = cleaned or page.original_path
            if progress_callback:
                await progress_callback("inpainting", page.page_number)

        await session.commit()

        for page in pages:
            page.status = "typesetting"
            await session.commit()
            translated_entries = [entry for entry in translation_entries if entry.page_id == page.id]
            page.translated_path = typeset_page(page, translated_entries)
            page.status = "done"
            if progress_callback:
                await progress_callback("typesetting", page.page_number)

        project.status = "review"
        project.processed_pages = project.total_pages
        await session.commit()
        if progress_callback:
            await progress_callback("completed")
