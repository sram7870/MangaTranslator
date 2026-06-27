"""Pydantic schemas for API responses."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ProjectResponse(BaseModel):
    """Project response schema."""
    id: str
    name: str
    source_language: str
    status: str
    total_pages: int
    processed_pages: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel):
    """Page response schema."""
    id: str
    project_id: str
    page_number: int
    original_file_path: str
    cleaned_file_path: Optional[str] = None
    translated_file_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TranslationResponse(BaseModel):
    """Translation entry response schema."""
    id: str
    page_id: str
    bubble_index: int
    original_text: str
    translated_text: str
    x: int
    y: int
    w: int
    h: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GlossaryResponse(BaseModel):
    """Glossary entry response schema."""
    id: str
    project_id: str
    original_term: str
    translated_term: str
    context: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class CharacterResponse(BaseModel):
    """Character response schema."""
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
