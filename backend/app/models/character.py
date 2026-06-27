import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name_original: Mapped[str] = mapped_column(String(200), nullable=False)
    name_translated: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(400), nullable=True)
    first_seen_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project = relationship("Project", back_populates="characters")
