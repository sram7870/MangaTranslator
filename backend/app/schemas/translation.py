from pydantic import BaseModel

class TranslationUpdate(BaseModel):
    translated_text: str
