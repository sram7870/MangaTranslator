from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

ROOT_DIR = Path(__file__).resolve().parents[2]
FONT_PATH = ROOT_DIR / "fonts" / "tiempos.ttf"


def _load_font(size: int):
    return ImageFont.truetype(str(FONT_PATH), size=size) if FONT_PATH.exists() else ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_height: int):
    safe_text = text.strip() or "..."
    for size in range(34, 11, -2):
        font = _load_font(size)
        chars_per_line = max(8, max_width // max(size // 2, 1))
        wrapped = "\n".join(textwrap.wrap(safe_text, width=chars_per_line) or [safe_text])
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=4, align="center")
        if bbox[2] - bbox[0] <= max_width and bbox[3] - bbox[1] <= max_height:
            return wrapped, font, bbox
    font = _load_font(12)
    wrapped = "\n".join(textwrap.wrap(safe_text, width=max(8, max_width // 6)) or [safe_text])
    return wrapped, font, draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=3, align="center")


def typeset_page(page, translation_entries):
    cleaned_path = Path(page.cleaned_path or page.original_path)
    image = Image.open(cleaned_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    for entry in translation_entries:
        x, y, w, h = entry.x, entry.y, entry.w, entry.h
        translated_text = entry.translated_text or entry.original_text or "..."
        padding = max(8, min(w, h) // 10)
        max_width = max(20, w - padding * 2)
        max_height = max(20, h - padding * 2)
        wrapped, font, bbox = _fit_text(draw, translated_text, max_width, max_height)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255, 220))
        draw.multiline_text(
            (x + (w - text_width) / 2, y + (h - text_height) / 2),
            wrapped,
            font=font,
            fill="black",
            spacing=4,
            align="center",
        )

    translated_path = cleaned_path.parent.parent / "translated" / cleaned_path.name
    translated_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(translated_path)
    return str(translated_path)
