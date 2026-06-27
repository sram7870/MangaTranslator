from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import create_tables
from .routers import projects, pages, translation, export, glossary, characters, process

app = FastAPI(title="AI Manga Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_dir = Path(settings.storage_path)
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

@app.on_event("startup")
async def on_startup():
    await create_tables()

app.include_router(projects.router)
app.include_router(pages.router)
app.include_router(translation.router)
app.include_router(export.router)
app.include_router(glossary.router)
app.include_router(characters.router)
app.include_router(process.router)
