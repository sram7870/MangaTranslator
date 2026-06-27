from typing import Dict

class TranslationMemory:
    def __init__(self):
        self.memory: Dict[str, str] = {}

    def get(self, original: str) -> str | None:
        return self.memory.get(original)

    def add(self, original: str, translation: str):
        self.memory[original] = translation

    def bulk_add(self, entries: dict[str, str]):
        self.memory.update(entries)

    def items(self):
        return self.memory.items()
