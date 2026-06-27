import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..config import settings
from ..models.project import Project
from ..models.page import Page
from ..schemas import ProjectDetail, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str
    source_language: str = "auto"


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/", response_model=ProjectResponse)
async def create_project(data: ProjectCreateRequest, db: AsyncSession = Depends(get_db)):
    project = Project(name=data.name, source_language=data.source_language)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    pages_result = await db.execute(select(Page).where(Page.project_id == project.id).order_by(Page.page_number.asc()))
    return ProjectDetail(
        id=project.id,
        name=project.name,
        source_language=project.source_language,
        status=project.status,
        total_pages=project.total_pages,
        processed_pages=project.processed_pages,
        created_at=project.created_at,
        updated_at=project.updated_at,
        pages=list(pages_result.scalars().all()),
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    project_folder = Path(settings.storage_path) / project_id
    if project_folder.exists():
        shutil.rmtree(project_folder)
    return {"detail": "Project deleted"}
