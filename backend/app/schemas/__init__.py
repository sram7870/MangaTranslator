# API schema package
from .project import ProjectCreate, ProjectDetail, ProjectResponse
from .page import PageCreateResponse
from .translation import TranslationUpdate
from .glossary import GlossaryEntryCreate, GlossaryEntryDetail
from .character import CharacterCreate, CharacterDetail

__all__ = [
    "ProjectCreate",
    "ProjectDetail",
    "ProjectResponse",
    "PageCreateResponse",
    "TranslationUpdate",
    "GlossaryEntryCreate",
    "GlossaryEntryDetail",
    "CharacterCreate",
    "CharacterDetail",
]
