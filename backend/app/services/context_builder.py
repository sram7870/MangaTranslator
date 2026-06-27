"""Context builder: calls the LLM to extract story context then persists it to the DB."""
from __future__ import annotations

from typing import List

from sqlalchemy import delete

from ..database import AsyncSessionLocal
from ..models.character import Character
from ..models.glossary import GlossaryEntry
from .translation_service import analyze_story_context, extract_glossary_terms


async def build_context(project_id: str, texts: List[str]) -> dict:
    """Analyse all extracted texts, save characters + glossary to DB, return context dict."""
    context = await analyze_story_context(texts)

    summary = context.get("summary", "")
    characters = context.get("characters") or []
    glossary_terms = context.get("glossary") or []
    tone = context.get("tone", "")

    async with AsyncSessionLocal() as session:
        # Clear existing context for a clean rebuild
        await session.execute(delete(GlossaryEntry).where(GlossaryEntry.project_id == project_id))
        await session.execute(delete(Character).where(Character.project_id == project_id))

        for item in characters:
            if not isinstance(item, dict):
                continue
            original = str(item.get("original") or item.get("name_original") or "").strip()
            translated = str(item.get("translated") or item.get("name_translated") or original).strip()
            if not original:
                continue
            session.add(Character(
                project_id=project_id,
                name_original=original,
                name_translated=translated,
                description=str(item.get("description") or "")[:400] or None,
                first_seen_page=int(item["first_seen_page"]) if item.get("first_seen_page") else 1,
            ))

        for item in glossary_terms:
            if not isinstance(item, dict):
                continue
            original = str(item.get("original") or item.get("term_original") or "").strip()
            translated = str(item.get("translated") or item.get("term_translated") or original).strip()
            category = str(item.get("category") or "general").strip() or "general"
            if not original:
                continue
            session.add(GlossaryEntry(
                project_id=project_id,
                term_original=original,
                term_translated=translated,
                category=category,
            ))

        await session.commit()

    return {
        "summary": summary,
        "tone": tone,
        "characters": characters,
        "glossary": glossary_terms,
    }


async def extract_terms(project_id: str, texts: List[str]) -> list[dict]:
    return await extract_glossary_terms(texts)
