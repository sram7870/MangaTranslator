import shutil
import tempfile
import zipfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import AsyncSessionLocal
from ..models.project import Project
from ..models.page import Page
from ..schemas.page import PageCreateResponse
from ..config import settings

router = APIRouter(prefix="/api/projects", tags=["pages"])
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
UPLOAD_SUFFIXES = IMAGE_SUFFIXES | {".pdf"}

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def _render_pdf_pages(pdf_path: Path, output_folder: Path, start_index: int) -> list[Path]:
    try:
        import fitz
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF upload requires PyMuPDF. Install backend requirements and restart the server.",
        ) from exc

    rendered_paths: list[Path] = []
    document = fitz.open(pdf_path)
    try:
        for offset, page in enumerate(document, start=0):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            destination = output_folder / f"page_{start_index + offset:03d}.png"
            pixmap.save(destination)
            rendered_paths.append(destination)
    finally:
        document.close()
    return rendered_paths


def _save_upload_as_images(upload_file: UploadFile, project_folder: Path, start_index: int) -> list[Path]:
    suffix = Path(upload_file.filename or "").suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        return []

    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            shutil.copyfileobj(upload_file.file, temp_file)
            temp_path = Path(temp_file.name)
        try:
            return _render_pdf_pages(temp_path, project_folder, start_index)
        finally:
            temp_path.unlink(missing_ok=True)

    destination = project_folder / f"page_{start_index:03d}{suffix}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return [destination]


def _create_page_records(project: Project, image_paths: list[Path]) -> list[Page]:
    pages = []
    for index, image_path in enumerate(image_paths, start=1):
        pages.append(
            Page(
                project_id=project.id,
                page_number=index,
                original_path=str(image_path),
                status="pending",
            )
        )
    return pages


@router.post("/{project_id}/pages", response_model=list[PageCreateResponse])
async def upload_pages(project_id: str, files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_folder = Path(settings.storage_path) / project_id / "originals"
    project_folder.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    for upload_file in files:
        image_paths.extend(_save_upload_as_images(upload_file, project_folder, len(image_paths) + 1))
        if len(image_paths) > settings.max_upload_pages:
            raise HTTPException(status_code=400, detail=f"Upload limit is {settings.max_upload_pages} rendered pages")

    pages = _create_page_records(project, image_paths)
    for page in pages:
        db.add(page)

    project.total_pages = len(pages)
    project.status = "uploading"
    await db.commit()
    for page in pages:
        await db.refresh(page)
    await db.refresh(project)
    return pages

@router.post("/{project_id}/pages/zip", response_model=list[PageCreateResponse])
async def upload_pages_zip(project_id: str, zip_file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / zip_file.filename
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(zip_file.file, buffer)

        with zipfile.ZipFile(temp_path, "r") as archive:
            files = [name for name in archive.namelist() if Path(name).suffix.lower() in UPLOAD_SUFFIXES]

            project_folder = Path(settings.storage_path) / project_id / "originals"
            project_folder.mkdir(parents=True, exist_ok=True)
            image_paths: list[Path] = []
            for index, member in enumerate(sorted(files), start=1):
                suffix = Path(member).suffix.lower()
                extracted = Path(temp_dir) / f"archive_{index:03d}{suffix}"
                extracted.write_bytes(archive.read(member))
                if suffix == ".pdf":
                    image_paths.extend(_render_pdf_pages(extracted, project_folder, len(image_paths) + 1))
                else:
                    destination = project_folder / f"page_{len(image_paths) + 1:03d}{suffix}"
                    destination.write_bytes(extracted.read_bytes())
                    image_paths.append(destination)
                if len(image_paths) > settings.max_upload_pages:
                    raise HTTPException(status_code=400, detail=f"Upload limit is {settings.max_upload_pages} rendered pages")

            pages = _create_page_records(project, image_paths)
            for page in pages:
                db.add(page)

    project.total_pages = len(pages)
    project.status = "uploading"
    await db.commit()
    for page in pages:
        await db.refresh(page)
    await db.refresh(project)
    return pages

@router.get("/{project_id}/pages", response_model=list[PageCreateResponse])
async def list_pages(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(Page).where(Page.project_id == project.id).order_by(Page.page_number.asc()))
    return result.scalars().all()

@router.get("/{project_id}/pages/{page_id}/image/{image_type}")
async def get_page_image(project_id: str, page_id: str, image_type: str, db: AsyncSession = Depends(get_db)):
    valid_types = {"original", "cleaned", "translated"}
    if image_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid image type")

    result = await db.execute(select(Page).where(Page.id == page_id, Page.project_id == project_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    path_attr = f"{image_type}_path"
    image_path = getattr(page, path_attr, None)
    if not image_path:
        raise HTTPException(status_code=404, detail=f"{image_type} image not available")
    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail=f"{image_type} image file is missing")

    return FileResponse(image_path)
