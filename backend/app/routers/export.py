import io
import zipfile
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from PIL import Image
from pathlib import Path

from ..models.page import Page
from ..database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/api/projects", tags=["export"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{project_id}/export/zip")
async def export_zip(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.project_id == project_id).order_by(Page.page_number.asc()))
    pages = result.scalars().all()
    if not pages:
        raise HTTPException(status_code=404, detail="No pages available")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for page in pages:
            if page.translated_path:
                archive.write(page.translated_path, Path(page.translated_path).name)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=translated_pages_{project_id}.zip"})

@router.get("/{project_id}/export/pdf")
async def export_pdf(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.project_id == project_id).order_by(Page.page_number.asc()))
    pages = result.scalars().all()
    if not pages:
        raise HTTPException(status_code=404, detail="No pages available")

    images = []
    for page in pages:
        if page.translated_path:
            images.append(Image.open(page.translated_path).convert("RGB"))
    if not images:
        raise HTTPException(status_code=404, detail="No translated images available")

    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=translated_pages_{project_id}.pdf"})

@router.get("/{project_id}/export/cbz")
async def export_cbz(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.project_id == project_id).order_by(Page.page_number.asc()))
    pages = result.scalars().all()
    if not pages:
        raise HTTPException(status_code=404, detail="No pages available")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for page in pages:
            if page.translated_path:
                archive.write(page.translated_path, Path(page.translated_path).name)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/vnd.comicbook+zip", headers={"Content-Disposition": f"attachment; filename=translated_pages_{project_id}.cbz"})


@router.get("/{project_id}/export/images/{image_format}")
async def export_images(project_id: str, image_format: str, db: AsyncSession = Depends(get_db)):
    normalized = image_format.lower()
    if normalized not in {"png", "jpg", "jpeg"}:
        raise HTTPException(status_code=400, detail="Image format must be png or jpg")

    result = await db.execute(select(Page).where(Page.project_id == project_id).order_by(Page.page_number.asc()))
    pages = result.scalars().all()
    if not pages:
        raise HTTPException(status_code=404, detail="No pages available")

    output_format = "JPEG" if normalized in {"jpg", "jpeg"} else "PNG"
    extension = "jpg" if output_format == "JPEG" else "png"
    media_type = "image/jpeg" if output_format == "JPEG" else "image/png"
    translated_pages = [page for page in pages if page.translated_path]
    if not translated_pages:
        raise HTTPException(status_code=404, detail="No translated images available")

    if len(translated_pages) == 1:
        buffer = io.BytesIO()
        Image.open(translated_pages[0].translated_path).convert("RGB").save(buffer, format=output_format)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=translated_page_001.{extension}"},
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for page in translated_pages:
            image_buffer = io.BytesIO()
            Image.open(page.translated_path).convert("RGB").save(image_buffer, format=output_format)
            archive.writestr(f"page_{page.page_number:03d}.{extension}", image_buffer.getvalue())
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=translated_pages_{project_id}_{extension}.zip"},
    )
