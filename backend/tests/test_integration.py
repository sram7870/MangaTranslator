"""Integration tests for the manga translator backend.

Run with:  pytest backend/tests/ -v
"""
from __future__ import annotations

import asyncio
import io
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

# Ensure we have a clean in-memory database for tests
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STORAGE_PATH", "/tmp/manga_test_storage")
os.environ.setdefault("DEVELOPMENT_MODE", "true")

from backend.app.main import app  # noqa: E402  (after env setup)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_png(width: int = 400, height: int = 600) -> bytes:
    """Return bytes of a minimal white PNG."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_test_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 400), color=(200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
def create_db():
    """Bootstrap tables once before all tests."""
    from backend.app.database import create_tables, engine, Base
    asyncio.get_event_loop().run_until_complete(create_tables())
    yield


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

class TestProjectCRUD:
    def test_create_project(self):
        resp = client.post("/api/projects/", json={"name": "Test Manga", "source_language": "ja"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Manga"
        assert data["source_language"] == "ja"
        assert "id" in data

    def test_list_projects(self):
        resp = client.get("/api/projects/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_project(self):
        create = client.post("/api/projects/", json={"name": "Get Test"})
        pid = create.json()["id"]
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_project_not_found(self):
        resp = client.get("/api/projects/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_project(self):
        create = client.post("/api/projects/", json={"name": "Delete Me"})
        pid = create.json()["id"]
        del_resp = client.delete(f"/api/projects/{pid}")
        assert del_resp.status_code == 200
        get_resp = client.get(f"/api/projects/{pid}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Page upload
# ---------------------------------------------------------------------------

class TestPageUpload:
    def _new_project(self, name: str = "Upload Test") -> str:
        return client.post("/api/projects/", json={"name": name}).json()["id"]

    def test_upload_png(self):
        pid = self._new_project()
        resp = client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("page1.png", _make_test_png(), "image/png"))],
        )
        assert resp.status_code == 200
        pages = resp.json()
        assert len(pages) >= 1
        assert pages[0]["page_number"] == 1

    def test_upload_jpeg(self):
        pid = self._new_project("JPEG Test")
        resp = client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("page1.jpg", _make_test_jpeg(), "image/jpeg"))],
        )
        assert resp.status_code == 200

    def test_upload_multiple_pages(self):
        pid = self._new_project("Multi")
        resp = client.post(
            f"/api/projects/{pid}/pages",
            files=[
                ("files", ("p1.png", _make_test_png(), "image/png")),
                ("files", ("p2.png", _make_test_png(), "image/png")),
            ],
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_upload_to_missing_project(self):
        resp = client.post(
            "/api/projects/bad-id/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        )
        assert resp.status_code == 404

    def test_list_pages(self):
        pid = self._new_project("List Pages")
        client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        )
        resp = client.get(f"/api/projects/{pid}/pages")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Image serving
# ---------------------------------------------------------------------------

class TestImageServing:
    def _upload_and_get_page_id(self) -> tuple[str, str]:
        pid = client.post("/api/projects/", json={"name": "Image Serve"}).json()["id"]
        pages = client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        ).json()
        return pid, pages[0]["id"]

    def test_get_original_image(self):
        pid, page_id = self._upload_and_get_page_id()
        resp = client.get(f"/api/projects/{pid}/pages/{page_id}/image/original")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/")

    def test_get_invalid_image_type(self):
        pid, page_id = self._upload_and_get_page_id()
        resp = client.get(f"/api/projects/{pid}/pages/{page_id}/image/garbage")
        assert resp.status_code == 400

    def test_missing_translated_image(self):
        pid, page_id = self._upload_and_get_page_id()
        resp = client.get(f"/api/projects/{pid}/pages/{page_id}/image/translated")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Translation endpoints
# ---------------------------------------------------------------------------

class TestTranslationEndpoints:
    def _project_with_translations(self) -> str:
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.translation import TranslationEntry
        from backend.app.models.page import Page as PageModel

        pid = client.post("/api/projects/", json={"name": "Trans Test"}).json()["id"]
        pages = client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        ).json()
        page_id = pages[0]["id"]

        async def _insert():
            async with AsyncSessionLocal() as s:
                s.add(TranslationEntry(
                    page_id=page_id,
                    bubble_index=0,
                    original_text="テスト",
                    translated_text="Test",
                    x=10, y=10, w=100, h=50,
                ))
                await s.commit()

        asyncio.get_event_loop().run_until_complete(_insert())
        return pid

    def test_get_translations(self):
        pid = self._project_with_translations()
        resp = client.get(f"/api/projects/{pid}/translations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["original_text"] == "テスト"

    def test_update_translation(self):
        pid = self._project_with_translations()
        entries = client.get(f"/api/projects/{pid}/translations").json()
        tid = entries[0]["id"]
        resp = client.put(
            f"/api/projects/{pid}/translations/{tid}",
            json={"translated_text": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["translated_text"] == "Updated"


# ---------------------------------------------------------------------------
# Glossary endpoints
# ---------------------------------------------------------------------------

class TestGlossaryEndpoints:
    def _project_with_glossary(self) -> tuple[str, str]:
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.glossary import GlossaryEntry

        pid = client.post("/api/projects/", json={"name": "Glossary Test"}).json()["id"]

        async def _insert():
            async with AsyncSessionLocal() as s:
                entry = GlossaryEntry(
                    project_id=pid,
                    term_original="武器",
                    term_translated="Weapon",
                    category="general",
                )
                s.add(entry)
                await s.commit()
                await s.refresh(entry)
                return entry.id

        gid = asyncio.get_event_loop().run_until_complete(_insert())
        return pid, gid

    def test_list_glossary(self):
        pid, _ = self._project_with_glossary()
        resp = client.get(f"/api/projects/{pid}/glossary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_update_glossary_entry(self):
        pid, gid = self._project_with_glossary()
        resp = client.put(
            f"/api/projects/{pid}/glossary/{gid}",
            json={"term_original": "武器", "term_translated": "Arms", "category": "general"},
        )
        assert resp.status_code == 200
        assert resp.json()["term_translated"] == "Arms"


# ---------------------------------------------------------------------------
# Character endpoints
# ---------------------------------------------------------------------------

class TestCharacterEndpoints:
    def _project_with_character(self) -> tuple[str, str]:
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.character import Character

        pid = client.post("/api/projects/", json={"name": "Char Test"}).json()["id"]

        async def _insert():
            async with AsyncSessionLocal() as s:
                ch = Character(
                    project_id=pid,
                    name_original="鬼滅",
                    name_translated="Kimetsu",
                    description="Hero",
                    first_seen_page=1,
                )
                s.add(ch)
                await s.commit()
                await s.refresh(ch)
                return ch.id

        cid = asyncio.get_event_loop().run_until_complete(_insert())
        return pid, cid

    def test_list_characters(self):
        pid, _ = self._project_with_character()
        resp = client.get(f"/api/projects/{pid}/characters")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_character(self):
        pid, cid = self._project_with_character()
        resp = client.put(
            f"/api/projects/{pid}/characters/{cid}",
            json={
                "name_original": "鬼滅",
                "name_translated": "Kimetsu Updated",
                "description": "Updated hero",
                "first_seen_page": 2,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name_translated"] == "Kimetsu Updated"


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

class TestExportEndpoints:
    def _project_with_translated_page(self) -> str:
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.page import Page as PageModel

        pid = client.post("/api/projects/", json={"name": "Export Test"}).json()["id"]
        pages = client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        ).json()
        page_id = pages[0]["id"]

        # Manually set translated_path to the original so exports work
        async def _patch():
            async with AsyncSessionLocal() as s:
                from sqlalchemy.future import select
                page = (await s.execute(
                    select(PageModel).where(PageModel.id == page_id)
                )).scalar_one()
                page.translated_path = page.original_path
                await s.commit()

        asyncio.get_event_loop().run_until_complete(_patch())
        return pid

    def test_export_zip(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        assert len(zf.namelist()) >= 1

    def test_export_pdf(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_export_cbz(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/cbz")
        assert resp.status_code == 200

    def test_export_png(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/images/png")
        assert resp.status_code == 200

    def test_export_jpg(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/images/jpg")
        assert resp.status_code == 200

    def test_export_invalid_format(self):
        pid = self._project_with_translated_page()
        resp = client.get(f"/api/projects/{pid}/export/images/bmp")
        assert resp.status_code == 400

    def test_export_empty_project(self):
        pid = client.post("/api/projects/", json={"name": "Empty"}).json()["id"]
        resp = client.get(f"/api/projects/{pid}/export/zip")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Processing pipeline (dev mode smoke test)
# ---------------------------------------------------------------------------

class TestProcessingPipeline:
    def test_start_process(self):
        pid = client.post("/api/projects/", json={"name": "Pipeline Test"}).json()["id"]
        client.post(
            f"/api/projects/{pid}/pages",
            files=[("files", ("p.png", _make_test_png(), "image/png"))],
        )
        resp = client.post(f"/api/projects/{pid}/process")
        assert resp.status_code == 200
        assert "detail" in resp.json()

    def test_process_nonexistent_project(self):
        resp = client.post("/api/projects/bad-id/process")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_project_response_schema(self):
        from backend.app.models.project import Project
        from backend.app.schemas.project import ProjectResponse

        p = Project(
            id="abc",
            name="Schema Test",
            source_language="ja",
            status="uploading",
            total_pages=3,
            processed_pages=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        schema = ProjectResponse.model_validate(p)
        assert schema.name == "Schema Test"
        assert schema.total_pages == 3

    def test_translation_update_schema(self):
        from backend.app.schemas.translation import TranslationUpdate
        schema = TranslationUpdate(translated_text="Hello")
        assert schema.translated_text == "Hello"


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestBubbleDetector:
    def test_pillow_fallback(self, tmp_path):
        from backend.app.services.bubble_detector import _pillow_fallback_detect

        img_path = tmp_path / "test.png"
        Image.new("RGB", (600, 800), "white").save(img_path)
        bubbles = _pillow_fallback_detect(img_path)
        assert isinstance(bubbles, list)
        assert len(bubbles) >= 1
        b = bubbles[0]
        assert "x" in b and "y" in b and "w" in b and "h" in b

    def test_detect_bubbles_returns_list(self, tmp_path):
        from backend.app.services.bubble_detector import detect_bubbles

        img_path = tmp_path / "test.png"
        Image.new("RGB", (400, 600), "white").save(img_path)
        result = detect_bubbles(img_path)
        assert isinstance(result, list)


class TestInpaintingService:
    def test_pillow_fill(self, tmp_path):
        from backend.app.services.inpainting_service import _pillow_fill

        img_path = tmp_path / "orig.png"
        Image.new("RGB", (400, 600), "white").save(img_path)
        bubbles = [{"x": 50, "y": 50, "w": 100, "h": 80}]
        result = _pillow_fill(img_path, bubbles)
        assert result is not None
        assert Path(result).exists()

    def test_build_mask(self):
        from backend.app.services.inpainting_service import _build_mask

        mask = _build_mask((400, 600), [{"x": 10, "y": 10, "w": 80, "h": 60}])
        assert mask.size == (400, 600)


class TestTypesettingService:
    def test_typeset_page(self, tmp_path):
        from backend.app.services.typesetting_service import typeset_page

        orig = tmp_path / "originals" / "page_001.png"
        orig.parent.mkdir(parents=True)
        Image.new("RGB", (400, 600), "white").save(orig)

        cleaned = tmp_path / "cleaned" / "page_001.png"
        cleaned.parent.mkdir(parents=True)
        Image.new("RGB", (400, 600), "white").save(cleaned)

        class FakePage:
            original_path = str(orig)
            cleaned_path = str(cleaned)

        class FakeEntry:
            x, y, w, h = 50, 50, 200, 80
            translated_text = "Hello world"
            original_text = "テスト"

        result = typeset_page(FakePage(), [FakeEntry()])
        assert result is not None
        assert Path(result).exists()


class TestTranslationService:
    def test_local_translate_known(self):
        from backend.app.services.translation_service import _local_translate
        assert _local_translate("こんにちは") == "Hello"

    def test_local_translate_unknown(self):
        from backend.app.services.translation_service import _local_translate
        result = _local_translate("unknown text")
        assert isinstance(result, str)

    def test_heuristic_context(self):
        from backend.app.services.translation_service import _heuristic_context
        ctx = _heuristic_context(["Hello World", "My name is Naruto"])
        assert "summary" in ctx
        assert "characters" in ctx
        assert "glossary" in ctx

    @pytest.mark.asyncio
    async def test_translate_batch_dev_mode(self):
        from backend.app.services.translation_service import translate_batch
        items = [
            {"bubble_index": 0, "text": "こんにちは"},
            {"bubble_index": 1, "text": "ありがとう"},
        ]
        results = await translate_batch(items)
        assert len(results) == 2
        for r in results:
            assert "bubble_index" in r
            assert "translated_text" in r

    def test_extract_json_plain(self):
        from backend.app.services.translation_service import _extract_json
        data = _extract_json('[{"bubble_index": 0, "translated_text": "Hi"}]')
        assert data[0]["translated_text"] == "Hi"

    def test_extract_json_fenced(self):
        from backend.app.services.translation_service import _extract_json
        raw = '```json\n[{"bubble_index": 0, "translated_text": "Hi"}]\n```'
        data = _extract_json(raw)
        assert data[0]["bubble_index"] == 0
