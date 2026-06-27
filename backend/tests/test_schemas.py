from datetime import datetime

from backend.app.models.project import Project
from backend.app.schemas.project import ProjectResponse


def test_project_response_model_validate_accepts_sqlalchemy_model():
    project = Project(
        id="project-123",
        name="Demo",
        source_language="en",
        status="uploading",
        total_pages=2,
        processed_pages=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = ProjectResponse.model_validate(project)

    assert response.name == "Demo"
    assert response.total_pages == 2
