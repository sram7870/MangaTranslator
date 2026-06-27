"""Typesetting service: renders translated text back onto cleaned manga pages."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[2]

# Preferred font paths, tried in order
_FONT_CANDIDATES = [
    ROOT_DIR / "fonts" / "AnimeAce2.ttf",
    ROOT_DIR / "fonts" / "tiempos.ttf",
    ROOT_DIR / "fonts" / "manga.ttf",
]


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                continue
    # PIL default bitmap font – always available
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Text fitting
# ---------------------------------------------------------------------------

_SFX_RE = re.compile(r"^[A-Z\s!?*]+$")  # All-caps → likely SFX


def _is_sfx(text: str) -> bool:
    return bool(_SFX_RE.match(text.strip())) and len(text.strip()) < 20


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    is_sfx: bool = False,
) -> tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont, tuple[int, int, int, int]]:
    """Find the largest font size where text fits inside the bubble."""
    safe_text = text.strip() or "..."

    start_size = 44 if is_sfx else 32
    min_size = 9

    for size in range(start_size, min_size - 1, -2):
        font = _load_font(size)
        # Estimate chars-per-line from font metrics
        try:
            sample_w = font.getlength("A")
        except AttributeError:
            sample_w = size * 0.6
        chars_per_line = max(6, int(max_width / max(sample_w, 1)))
        wrapped = "\n".join(textwrap.wrap(safe_text, width=chars_per_line) or [safe_text])
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=4, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= max_width and text_h <= max_height:
            return wrapped, font, bbox

    # Force fit at minimum size
    font = _load_font(min_size)
    wrapped = "\n".join(textwrap.wrap(safe_text, width=max(4, max_width // max(min_size // 2, 1))) or [safe_text])
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=3, align="center")
    return wrapped, font, bbox


# ---------------------------------------------------------------------------
# Per-bubble rendering
# ---------------------------------------------------------------------------

def _render_bubble(
    draw: ImageDraw.ImageDraw,
    entry,
    image_width: int,
    image_height: int,
) -> None:
    x, y, w, h = entry.x, entry.y, entry.w, entry.h
    text = (entry.translated_text or entry.original_text or "").strip()
    if not text:
        return

    # Clamp to image bounds
    x = max(0, min(x, image_width - 1))
    y = max(0, min(y, image_height - 1))
    w = max(10, min(w, image_width - x))
    h = max(10, min(h, image_height - y))

    sfx = _is_sfx(text)
    padding = max(6, min(w, h) // 10)
    max_w = max(10, w - padding * 2)
    max_h = max(10, h - padding * 2)

    wrapped, font, bbox = _fit_text(draw, text, max_w, max_h, is_sfx=sfx)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # White background for the bubble area (clean slate)
    draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255, 230))

    # Centre text in bubble
    text_x = x + (w - text_w) / 2
    text_y = y + (h - text_h) / 2

    # Shadow / outline for SFX text
    if sfx:
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            draw.multiline_text(
                (text_x + dx, text_y + dy),
                wrapped,
                font=font,
                fill=(180, 0, 0),
                spacing=4,
                align="center",
            )

    fill_color = (20, 20, 20) if not sfx else (0, 0, 0)
    draw.multiline_text(
        (text_x, text_y),
        wrapped,
        font=font,
        fill=fill_color,
        spacing=4,
        align="center",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def typeset_page(page, translation_entries: list) -> str:
    """Render all translation entries onto the cleaned (or original) page image.

    Returns the path to the translated output image.
    """
    source_path = Path(page.cleaned_path or page.original_path)
    image = Image.open(source_path).convert("RGBA")
    draw = ImageDraw.Draw(image)
    iw, ih = image.size

    for entry in translation_entries:
        try:
            _render_bubble(draw, entry, iw, ih)
        except Exception:
            # Never crash the whole pipeline over one bad bubble
            continue

    # Save as RGB PNG (RGBA doesn't work for JPEG)
    output = image.convert("RGB")
    translated_dir = source_path.parent.parent / "translated"
    translated_dir.mkdir(parents=True, exist_ok=True)
    dest = translated_dir / source_path.name
    output.save(dest, quality=95)
    return str(dest)
