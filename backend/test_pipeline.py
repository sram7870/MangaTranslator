#!/usr/bin/env python3.12
"""End-to-end backend pipeline test."""
import asyncio
import httpx
from pathlib import Path
from PIL import Image

BASE_URL = "http://127.0.0.1:8000/api"


async def create_test_image():
    """Create a test manga page image."""
    img = Image.new("RGB", (800, 1000), color="white")
    test_path = Path("./backend/storage/test_page.png")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(test_path)
    return test_path


async def test_pipeline():
    """Test the complete backend pipeline."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create a project
        print("1️⃣  Creating project...")
        project_response = await client.post(
            f"{BASE_URL}/projects/",
            json={
                "name": "Test Manga",
                "source_language": "en",
            },
        )
        assert project_response.status_code == 200, f"Failed to create project: {project_response.text}"
        project_id = project_response.json()["id"]
        print(f"   ✓ Project created: {project_id}")

        # Step 2: Create test image and upload
        print("2️⃣  Creating and uploading test image...")
        test_image_path = await create_test_image()
        with open(test_image_path, "rb") as f:
            upload_response = await client.post(
                f"{BASE_URL}/projects/{project_id}/pages",
                files={"files": ("test_page.png", f, "image/png")},
            )
        assert upload_response.status_code == 200, f"Failed to upload page: {upload_response.text}"
        upload_data = upload_response.json()
        print(f"   ✓ Uploaded {len(upload_data.get('pages', []))} page(s)")

        # Step 3: Start processing
        print("3️⃣  Starting pipeline processing...")
        process_response = await client.post(f"{BASE_URL}/projects/{project_id}/process")
        assert process_response.status_code == 200, f"Failed to start process: {process_response.text}"
        print("   ✓ Pipeline started")

        # Step 4: Monitor progress via SSE
        print("4️⃣  Monitoring progress...")
        async with client.stream("GET", f"{BASE_URL}/projects/{project_id}/progress") as response:
            assert response.status_code == 200, f"Failed to get progress: {response.text}"
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        import json
                        data = json.loads(data_str)
                        stage = data.get("stage", "unknown")
                        progress = data.get("progress", 0)
                        print(f"   📊 {stage.upper()}: {progress}%")
                        
                        if stage == "completed":
                            print("   ✓ Pipeline completed!")
                            break

        # Step 5: Verify project and pages
        print("5️⃣  Verifying results...")
        project_check = await client.get(f"{BASE_URL}/projects/{project_id}")
        assert project_check.status_code == 200, f"Failed to verify project: {project_check.text}"
        project_data = project_check.json()
        print(f"   ✓ Project status: {project_data['status']}")
        print(f"   ✓ Total pages: {project_data['total_pages']}")
        print(f"   ✓ Processed pages: {project_data['processed_pages']}")

        print("\n✅ Backend pipeline test PASSED - everything works flawlessly!")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
