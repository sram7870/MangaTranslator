from pathlib import Path
from typing import List

from ..config import settings
from ..models.page import Page

Bubble = dict
_YOLO_MODEL = None


def _yolo_detect(image_path: Path) -> List[Bubble] | None:
    global _YOLO_MODEL
    try:
        from ultralytics import YOLO
    except Exception:
        return None

    try:
        if _YOLO_MODEL is None:
            _YOLO_MODEL = YOLO(settings.bubble_detector_model)
        results = _YOLO_MODEL.predict(str(image_path), conf=settings.bubble_detector_confidence, verbose=False)
    except Exception:
        return None

    bubbles: list[Bubble] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        masks_xy = []
        if getattr(result, "masks", None) is not None and getattr(result.masks, "xy", None) is not None:
            masks_xy = result.masks.xy

        for index, box in enumerate(boxes):
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = [int(round(value)) for value in xyxy]
            confidence = float(box.conf[0].item()) if box.conf is not None else 0.0
            class_id = int(box.cls[0].item()) if box.cls is not None else 0
            bubble: Bubble = {
                "x": max(0, x1),
                "y": max(0, y1),
                "w": max(1, x2 - x1),
                "h": max(1, y2 - y1),
                "confidence": confidence,
                "class": "bubble",
                "class_id": class_id,
                "detector": "yolo",
            }
            if index < len(masks_xy):
                bubble["mask"] = [[int(point[0]), int(point[1])] for point in masks_xy[index].tolist()]
            bubbles.append(bubble)

    return bubbles


def _opencv_detect(image_path: Path) -> List[Bubble] | None:
    try:
        import cv2
    except Exception:
        return None

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []

    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 220, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bubbles = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 50 or h < 50:
            continue
        bubbles.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "confidence": 0.75, "class": "bubble", "detector": "opencv"})

    return bubbles


def _pillow_fallback_detect(image_path: Path) -> List[Bubble]:
    from PIL import Image

    try:
        image = Image.open(image_path).convert("L")
    except Exception:
        return []

    width, height = image.size
    if width < 80 or height < 80:
        return []

    # Dependency-light fallback for local development: pick a plausible speech
    # bubble area near the top-center so the rest of the pipeline can run.
    box_width = max(80, int(width * 0.55))
    box_height = max(60, int(height * 0.18))
    x = max(0, (width - box_width) // 2)
    y = max(0, int(height * 0.08))
    return [{"x": x, "y": y, "w": box_width, "h": box_height, "confidence": 0.2, "class": "fallback", "detector": "pillow"}]


def detect_bubbles(image_path: Path) -> List[Bubble]:
    bubbles = _yolo_detect(image_path)
    if bubbles is None:
        bubbles = _opencv_detect(image_path)
    if bubbles is None:
        bubbles = _pillow_fallback_detect(image_path)

    bubbles.sort(key=lambda item: (item["y"], item["x"]))
    return bubbles

async def detect_page_bubbles(page: Page):
    from pathlib import Path
    image_path = Path(page.original_path)
    page.bubbles = detect_bubbles(image_path)
    return page.bubbles
