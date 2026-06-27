import uuid
from sqlalchemy import String, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_path: Mapped[str] = mapped_column(String(400), nullable=False)
    cleaned_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
    translated_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    bubbles: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project = relationship("Project", back_populates="pages")
    translations = relationship("TranslationEntry", back_populates="page", cascade="all, delete-orphan")
