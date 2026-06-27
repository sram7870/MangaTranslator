from pathlib import Path
import io
import zipfile
from PIL import Image

from ..models.page import Page

async def build_zip(pages: list[Page], filename: str) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for page in pages:
            if page.translated_path:
                archive.write(page.translated_path, Path(page.translated_path).name)
    buffer.seek(0)
    return buffer

async def build_pdf(pages: list[Page]) -> io.BytesIO:
    images = [Image.open(page.translated_path).convert("RGB") for page in pages if page.translated_path]
    buffer = io.BytesIO()
    if images:
        images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    buffer.seek(0)
    return buffer

async def build_cbz(pages: list[Page], filename: str) -> io.BytesIO:
    return await build_zip(pages, filename)
