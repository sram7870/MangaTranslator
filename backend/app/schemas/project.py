from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str
    source_language: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    source_language: str | None = None
    status: str
    total_pages: int
    processed_pages: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PageSummary(BaseModel):
    id: str
    page_number: int
    status: str
    original_path: str
    cleaned_path: str | None
    translated_path: str | None

    model_config = ConfigDict(from_attributes=True)

class ProjectDetail(BaseModel):
    id: str
    name: str
    source_language: str | None
    status: str
    total_pages: int
    processed_pages: int
    created_at: datetime
    updated_at: datetime
    pages: List[PageSummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
