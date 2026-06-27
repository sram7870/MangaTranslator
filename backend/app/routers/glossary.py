from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.project import Project
from ..models.glossary import GlossaryEntry
from ..schemas.glossary import GlossaryEntryCreate, GlossaryEntryDetail

router = APIRouter(prefix="/api/projects", tags=["glossary"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{project_id}/glossary", response_model=list[GlossaryEntryDetail])
async def list_glossary(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(select(GlossaryEntry).where(GlossaryEntry.project_id == project.id))
    return result.scalars().all()

@router.put("/{project_id}/glossary/{glossary_id}", response_model=GlossaryEntryDetail)
async def update_glossary(project_id: str, glossary_id: str, payload: GlossaryEntryCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GlossaryEntry).where(GlossaryEntry.id == glossary_id, GlossaryEntry.project_id == project_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary entry not found")
    entry.term_original = payload.term_original
    entry.term_translated = payload.term_translated
    entry.category = payload.category or "general"
    await db.commit()
    await db.refresh(entry)
    return entry
