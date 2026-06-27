import re
from typing import List

def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    return " ".join(text.split())

def detect_language(text: str) -> str:
    """Detect source language from text."""
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return "japanese"
        elif re.search(r'[\uAC00-\uD7A3]', text):
            return "korean"
        else:
            return "chinese"
    return "unknown"

def split_text_to_lines(text: str, max_width: int = 30) -> List[str]:
    """Split text into lines with max width."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_width:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def extract_terms(text: str) -> List[str]:
    """Extract potential terminology (capitalized words) from text."""
    words = text.split()
    return [w for w in words if w[0].isupper() and len(w) > 2]
