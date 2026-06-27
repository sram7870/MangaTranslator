import shutil
from pathlib import Path
from zipfile import ZipFile
from typing import List

from ..config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_EXTENSIONS

def save_uploaded_files(project_id: str, files: list[tuple[str, bytes]]) -> list[Path]:
    project_folder = Path(settings.storage_path) / project_id / "originals"
    project_folder.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    for index, (filename, content) in enumerate(files, start=1):
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            continue
        destination = project_folder / f"page_{index:03d}{extension}"
        destination.write_bytes(content)
        saved_paths.append(destination)

    return saved_paths

def extract_zip_images(zip_path: Path, target_folder: Path) -> List[Path]:
    target_folder.mkdir(parents=True, exist_ok=True)
    extracted = []
    with ZipFile(zip_path, "r") as archive:
        for member in sorted(archive.namelist()):
            path = Path(member)
            if path.suffix.lower() in ALLOWED_EXTENSIONS and not path.name.startswith("__MACOSX"):
                destination = target_folder / path.name
                destination.write_bytes(archive.read(member))
                extracted.append(destination)
    return extracted
