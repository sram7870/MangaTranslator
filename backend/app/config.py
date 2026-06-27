from pathlib import Path
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./backend/storage/database.db"
    storage_path: Path = Path("./backend/storage")
    model_path: Path = Path("./backend/models")
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    openai_model: str = "gpt-4o-mini"
    bubble_detector_model: str = "ogkalu/comic-speech-bubble-detector-yolov8m"
    bubble_detector_confidence: float = 0.45
    inpainting_model: str = "lama"
    frontend_origin: AnyHttpUrl = "http://localhost:5173"
    max_upload_pages: int = 5
    development_mode: bool = True

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()
