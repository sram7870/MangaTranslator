from pathlib import Path
from PIL import Image, ImageDraw

from ..config import settings
from ..models.page import Page


def _build_mask(path: Path, bubbles: list[dict]) -> Image.Image | None:
    try:
        image = Image.open(path)
    except Exception:
        return None

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    for bubble in bubbles:
        if bubble.get("mask"):
            draw.polygon([tuple(point) for point in bubble["mask"]], fill=255)
            continue
        x, y, w, h = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
        padding = max(3, min(w, h) // 18)
        draw.rounded_rectangle(
            [x + padding, y + padding, x + w - padding, y + h - padding],
            radius=max(8, min(w, h) // 8),
            fill=255,
        )
    return mask


def _lama_inpaint(path: Path, bubbles: list[dict]) -> str | None:
    mask = _build_mask(path, bubbles)
    if mask is None:
        return None

    try:
        import numpy as np
        from iopaint.model_manager import ModelManager
        from iopaint.schema import InpaintRequest
    except Exception:
        return None

    try:
        image = Image.open(path).convert("RGB")
        model = ModelManager(name=settings.inpainting_model, device="cpu")
        request = InpaintRequest()
        result = model(image=np.array(image), mask=np.array(mask), config=request)
        cleaned = Image.fromarray(result).convert("RGB")
    except Exception:
        return None

    cleaned_path = path.parent.parent / "cleaned" / path.name
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.save(cleaned_path)
    return str(cleaned_path)


def _opencv_inpaint(path: Path, bubbles: list[dict]) -> str | None:
    try:
        import cv2
        import numpy as np
    except Exception:
        return None

    image = cv2.imread(str(path))
    if image is None:
        return None

    pil_mask = _build_mask(path, bubbles)
    if pil_mask is None:
        return None
    mask = np.array(pil_mask, dtype=np.uint8)

    result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
    cleaned_path = path.parent.parent / "cleaned" / path.name
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(cleaned_path), result)
    return str(cleaned_path)


def _pillow_fill(path: Path, bubbles: list[dict]) -> str | None:
    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return None

    draw = ImageDraw.Draw(image)
    for bubble in bubbles:
        x, y, w, h = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
        draw.rounded_rectangle([x, y, x + w, y + h], radius=max(8, min(w, h) // 8), fill="white")

    cleaned_path = path.parent.parent / "cleaned" / path.name
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(cleaned_path)
    return str(cleaned_path)


def inpaint_page_image(page: Page):
    path = Path(page.original_path)
    bubbles = page.bubbles or []
    if not bubbles:
        return None

    return _lama_inpaint(path, bubbles) or _opencv_inpaint(path, bubbles) or _pillow_fill(path, bubbles)
