# AI Manga Translator

A local full-stack manga/manhwa/manhua translation workspace. The app can create projects, upload image pages or PDFs, process pages through OCR/translation/inpainting/typesetting, preview translated pages, and export translated output as PDF, PNG, JPG, ZIP, or CBZ.

## Current Status

Implemented and runnable:

- React + Vite frontend
- FastAPI backend
- SQLite persistence via SQLAlchemy async
- Image upload for JPG, PNG, and WEBP
- PDF upload rendered into page PNGs with PyMuPDF
- Project deletion with storage-folder cleanup
- Speech-bubble detection with OpenCV when available, plus a Pillow fallback
- OCR with Tesseract first, then Gemini Vision/OpenAI Vision fallback when configured
- Gemini translation first, OpenAI fallback second when `DEVELOPMENT_MODE=false`
- Development-mode OCR/translation fallback when `DEVELOPMENT_MODE=true`
- Basic inpainting and typesetting
- Preview modal with scroll mode and flip mode
- Export/download as PDF, PNG, JPG, ZIP, or CBZ

## Quick Start

### 1. Backend

```powershell
cd C:\Users\ramne\WebstormProjects\MangaTranslater
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend

```powershell
cd C:\Users\ramne\WebstormProjects\MangaTranslater\frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Vite may choose another port if `5173` is busy. Use the URL printed by Vite.

## Environment

Copy `backend\.env.example` to `backend\.env` if needed.

Important settings:

- `DEVELOPMENT_MODE=false` uses real providers. Gemini is attempted first when `GEMINI_API_KEY` is set, then OpenAI when `OPENAI_API_KEY` is set.
- `DEVELOPMENT_MODE=true` lets the pipeline run locally without live providers. OCR returns placeholder text and translation uses local fallback behavior.
- `GEMINI_MODEL=gemini-1.5-flash` controls Gemini text and vision calls.
- `OPENAI_MODEL=gpt-4o-mini` controls OpenAI text and vision fallback calls.
- `MAX_UPLOAD_PAGES=5` limits rendered pages per upload batch.

Do not commit real API keys.

## Verification

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
```

Frontend build:

```powershell
cd frontend
npm run build
```

Smoke-tested locally:

- Project list cleared to zero records
- Project creation and deletion work
- PDF upload renders into image page records
- Frontend production build succeeds
- Backend tests pass

## Still To Improve

- Replace simple bubble detection with a manga-specific YOLO/segmentation model.
- Upgrade cleanup from OpenCV/Pillow inpainting to LaMa/IOPaint quality.
- Add stronger story context extraction for names, glossary terms, and recurring terminology.
- Add batch translation with structured JSON validation instead of one bubble at a time.
- Improve typesetting with licensed manga fonts, vertical text handling, SFX styling, and better bubble-aware layout.
- Add automated integration tests for PDF upload, processing, preview image serving, and all export formats.
