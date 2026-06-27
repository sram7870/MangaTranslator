import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.project import Project
from ..pipeline.pipeline import process_project

router = APIRouter(prefix="/api/projects", tags=["process"])
progress_store: dict[str, str] = {}

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/{project_id}/process")
async def start_process(project_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def run():
        progress_store[project_id] = "started"

        async def progress_callback(stage: str, page_number: int | None = None):
            progress_store[project_id] = f"{stage}:{page_number or -1}"

        try:
            await process_project(project_id, progress_callback)
            progress_store[project_id] = "completed"
        except Exception:
            progress_store[project_id] = "error"

    background_tasks.add_task(run)
    return {"detail": "Processing started"}

@router.get("/{project_id}/progress")
async def progress_stream(project_id: str) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            status = progress_store.get(project_id, "idle")
            yield f"data: {status}\n\n"
            if status in {"completed", "error"}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
