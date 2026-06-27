from pydantic import BaseModel, ConfigDict


class CharacterCreate(BaseModel):
    name_original: str
    name_translated: str
    description: str | None = None
    first_seen_page: int | None = None


class CharacterDetail(CharacterCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)
