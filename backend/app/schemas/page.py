from pydantic import BaseModel, ConfigDict


class PageCreateResponse(BaseModel):
    id: str
    page_number: int
    original_path: str
    status: str

    model_config = ConfigDict(from_attributes=True)
