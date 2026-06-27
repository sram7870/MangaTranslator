from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.page import Page
from ..models.translation import TranslationEntry
from ..schemas.translation import TranslationUpdate

router = APIRouter(prefix="/api/projects", tags=["translation"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{project_id}/translations")
async def get_translations(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TranslationEntry).join(Page).where(Page.project_id == project_id))
    return result.scalars().all()

@router.put("/{project_id}/translations/{translation_id}")
async def update_translation(project_id: str, translation_id: str, payload: TranslationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TranslationEntry).where(TranslationEntry.id == translation_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Translation entry not found")
    entry.translated_text = payload.translated_text
    await db.commit()
    await db.refresh(entry)
    return entry
