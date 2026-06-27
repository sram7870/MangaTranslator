from pydantic import BaseModel, ConfigDict


class GlossaryEntryCreate(BaseModel):
    term_original: str
    term_translated: str
    category: str | None = "general"


class GlossaryEntryDetail(GlossaryEntryCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)
