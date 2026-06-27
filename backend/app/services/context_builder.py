from typing import List

from sqlalchemy import delete

from ..database import AsyncSessionLocal
from ..models.character import Character
from ..models.glossary import GlossaryEntry
from .translation_service import analyze_story_context, extract_glossary_terms


async def build_context(project_id: str, texts: List[str]):
    context = await analyze_story_context(texts)
    summary = context["summary"]
    glossary_terms = context.get("glossary", [])
    characters = context.get("characters", [])

    async with AsyncSessionLocal() as session:
        await session.execute(delete(GlossaryEntry).where(GlossaryEntry.project_id == project_id))
        await session.execute(delete(Character).where(Character.project_id == project_id))
        for character_item in characters:
            original = character_item.get("original") or character_item.get("name_original")
            translated = character_item.get("translated") or character_item.get("name_translated") or original
            if not original:
                continue
            session.add(
                Character(
                    project_id=project_id,
                    name_original=original,
                    name_translated=translated,
                    description=character_item.get("description"),
                    first_seen_page=character_item.get("first_seen_page") or 1,
                )
            )
        for glossary_item in glossary_terms:
            original = glossary_item.get("original") or glossary_item.get("term_original")
            translated = glossary_item.get("translated") or glossary_item.get("term_translated") or original
            category = glossary_item.get("category", "general")
            if not original:
                continue
            session.add(
                GlossaryEntry(
                    project_id=project_id,
                    term_original=original,
                    term_translated=translated,
                    category=category,
                )
            )
        await session.commit()

    return {
        "summary": summary,
        "tone": context.get("tone"),
        "characters": characters,
        "glossary": glossary_terms,
    }


async def extract_terms(project_id: str, texts: List[str]):
    return await extract_glossary_terms(texts)
