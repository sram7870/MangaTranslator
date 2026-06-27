"""Inpainting service: LaMa → OpenCV TELEA → Pillow white-fill fallback."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..config import settings
from ..models.page import Page


# ---------------------------------------------------------------------------
# Mask building
# ---------------------------------------------------------------------------

def _build_mask(image_size: tuple[int, int], bubbles: list[dict]) -> Image.Image:
    """Build a binary mask (white = erase) from bubble geometry."""
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)

    for bubble in bubbles:
        if bubble.get("mask"):
            points = [tuple(pt) for pt in bubble["mask"]]
            if len(points) >= 3:
                draw.polygon(points, fill=255)
            continue

        x, y, w, h = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
        # Small inward padding so we don't erase the bubble border
        padding = max(2, min(w, h) // 20)
        radius = max(6, min(w, h) // 6)
        draw.rounded_rectangle(
            [x + padding, y + padding, x + w - padding, y + h - padding],
            radius=radius,
            fill=255,
        )

    # Slight dilation so stray ink pixels at edges get covered
    return mask.filter(ImageFilter.MaxFilter(3))


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

def _lama_inpaint(path: Path, bubbles: list[dict]) -> str | None:
    """IOPaint / LaMa high-quality inpainting."""
    try:
        import numpy as np
        from iopaint.model_manager import ModelManager
        from iopaint.schema import InpaintRequest
    except ImportError:
        return None

    try:
        image = Image.open(path).convert("RGB")
        mask = _build_mask(image.size, bubbles)

        model = ModelManager(name=settings.inpainting_model, device="cpu")
        request = InpaintRequest()
        result_array = model(
            image=np.array(image),
            mask=np.array(mask),
            config=request,
        )
        cleaned = Image.fromarray(result_array).convert("RGB")
    except Exception:
        return None

    return _save_cleaned(cleaned, path)


def _opencv_inpaint(path: Path, bubbles: list[dict]) -> str | None:
    """OpenCV TELEA inpainting — good quality, no heavy dependencies."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    image_bgr = cv2.imread(str(path))
    if image_bgr is None:
        return None

    pil_image = Image.open(path).convert("RGB")
    mask = _build_mask(pil_image.size, bubbles)
    mask_np = np.array(mask, dtype=np.uint8)

    # Dilate mask slightly for cleaner edges
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_np = cv2.dilate(mask_np, kernel, iterations=1)

    result = cv2.inpaint(image_bgr, mask_np, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    return _save_cleaned(pil_result, path)


def _pillow_fill(path: Path, bubbles: list[dict]) -> str | None:
    """Simple white fill — always available, no quality guarantees."""
    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return None

    mask = _build_mask(image.size, bubbles)
    # Paste white where mask is active
    white = Image.new("RGB", image.size, (255, 255, 255))
    image.paste(white, mask=mask)
    return _save_cleaned(image, path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_cleaned(image: Image.Image, original_path: Path) -> str:
    cleaned_dir = original_path.parent.parent / "cleaned"
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    dest = cleaned_dir / original_path.name
    image.save(dest, quality=95)
    return str(dest)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inpaint_page_image(page: Page) -> str | None:
    """Inpaint all speech bubbles in a page image. Returns path to cleaned image."""
    path = Path(page.original_path)
    bubbles: list[dict] = page.bubbles or []

    if not bubbles:
        return None

    return (
        _lama_inpaint(path, bubbles)
        or _opencv_inpaint(path, bubbles)
        or _pillow_fill(path, bubbles)
    )
