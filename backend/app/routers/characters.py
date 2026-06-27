from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.project import Project
from ..models.character import Character
from ..schemas.character import CharacterCreate, CharacterDetail

router = APIRouter(prefix="/api/projects", tags=["characters"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{project_id}/characters", response_model=list[CharacterDetail])
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(select(Character).where(Character.project_id == project.id))
    return result.scalars().all()

@router.put("/{project_id}/characters/{character_id}", response_model=CharacterDetail)
async def update_character(project_id: str, character_id: str, payload: CharacterCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Character).where(Character.id == character_id, Character.project_id == project_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    character.name_original = payload.name_original
    character.name_translated = payload.name_translated
    character.description = payload.description
    character.first_seen_page = payload.first_seen_page
    await db.commit()
    await db.refresh(character)
    return character
