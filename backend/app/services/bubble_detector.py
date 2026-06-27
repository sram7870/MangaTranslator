"""Speech bubble detection with YOLO → OpenCV → Pillow fallback chain."""
from __future__ import annotations

from pathlib import Path
from typing import List

from ..config import settings
from ..models.page import Page

Bubble = dict
_YOLO_MODEL = None


def _yolo_detect(image_path: Path) -> List[Bubble] | None:
    """Try YOLO-based manga-specific bubble detection."""
    global _YOLO_MODEL
    try:
        from ultralytics import YOLO
    except ImportError:
        return None

    try:
        if _YOLO_MODEL is None:
            _YOLO_MODEL = YOLO(settings.bubble_detector_model)
        results = _YOLO_MODEL.predict(
            str(image_path),
            conf=settings.bubble_detector_confidence,
            verbose=False,
            iou=0.4,
        )
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
            x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
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
                bubble["mask"] = [
                    [int(pt[0]), int(pt[1])] for pt in masks_xy[index].tolist()
                ]
            bubbles.append(bubble)

    return bubbles if bubbles else None


def _opencv_detect(image_path: Path) -> List[Bubble] | None:
    """OpenCV-based heuristic bubble detection."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None

    height, width = image.shape

    # Adaptive threshold works better for varied manga styles
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4
    )

    # Morphological close to fill bubble interiors
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
    morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bubbles: list[Bubble] = []
    min_area = (width * height) * 0.005  # at least 0.5% of page area
    max_area = (width * height) * 0.5    # at most 50% of page

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        if w < 40 or h < 30:
            continue
        # Filter out very elongated shapes that aren't bubbles
        aspect = w / h if h > 0 else 0
        if aspect > 8 or aspect < 0.15:
            continue

        bubbles.append({
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
            "confidence": 0.65,
            "class": "bubble",
            "detector": "opencv",
        })

    return bubbles if bubbles else None


def _pillow_fallback_detect(image_path: Path) -> List[Bubble]:
    """Minimal fallback — picks a plausible bubble region so the pipeline keeps running."""
    from PIL import Image

    try:
        image = Image.open(image_path).convert("L")
    except Exception:
        return []

    width, height = image.size
    if width < 80 or height < 80:
        return []

    # Heuristically place two bubble regions (top and middle of page)
    results = []
    for frac_y, frac_h in [(0.06, 0.16), (0.35, 0.16)]:
        bw = max(80, int(width * 0.55))
        bh = max(50, int(height * frac_h))
        bx = max(0, (width - bw) // 2)
        by = max(0, int(height * frac_y))
        results.append({
            "x": bx,
            "y": by,
            "w": bw,
            "h": bh,
            "confidence": 0.15,
            "class": "fallback",
            "detector": "pillow",
        })

    return results


def _deduplicate(bubbles: List[Bubble], iou_threshold: float = 0.5) -> List[Bubble]:
    """Remove overlapping duplicate detections (simple greedy NMS)."""
    if not bubbles:
        return bubbles

    def box_area(b: Bubble) -> float:
        return b["w"] * b["h"]

    def iou(a: Bubble, b: Bubble) -> float:
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
        bx1, by1 = b["x"], b["y"]
        bx2, by2 = bx1 + b["w"], by1 + b["h"]
        inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
        inter_h = max(0, min(ay2, by2) - max(ay1, by1))
        inter = inter_w * inter_h
        union = box_area(a) + box_area(b) - inter
        return inter / union if union > 0 else 0.0

    sorted_bubbles = sorted(bubbles, key=lambda x: -x.get("confidence", 0))
    kept: list[Bubble] = []
    for candidate in sorted_bubbles:
        if all(iou(candidate, k) < iou_threshold for k in kept):
            kept.append(candidate)
    return kept


def detect_bubbles(image_path: Path) -> List[Bubble]:
    """Main entry: returns sorted, deduplicated bubbles for a page image."""
    bubbles = _yolo_detect(image_path)
    if not bubbles:
        bubbles = _opencv_detect(image_path)
    if not bubbles:
        bubbles = _pillow_fallback_detect(image_path)

    bubbles = _deduplicate(bubbles or [])
    bubbles.sort(key=lambda b: (b["y"], b["x"]))
    return bubbles


async def detect_page_bubbles(page: Page) -> List[Bubble]:
    image_path = Path(page.original_path)
    page.bubbles = detect_bubbles(image_path)
    return page.bubbles
