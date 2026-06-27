from pathlib import Path
from typing import List
import base64
import io
import httpx
from PIL import Image

from ..config import settings

OCRResult = dict


def _crop_png_data(crop: Image.Image) -> str:
    buffer = io.BytesIO()
    crop.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _ocr_with_gemini(crop: Image.Image) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini OCR fallback.")
    image_data = _crop_png_data(crop)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Extract only the original text visible in this manga/manhwa speech bubble. "
                            "Return plain text only. If no readable text is present, return an empty string."
                        )
                    },
                    {"inline_data": {"mime_type": "image/png", "data": image_data}},
                ],
            }
        ],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200},
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
    response.raise_for_status()
    parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def _ocr_with_openai(crop: Image.Image) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI OCR fallback.")
    image_data = _crop_png_data(crop)
    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract only the original text visible in this manga/manhwa speech bubble. "
                            "Return plain text only. If no readable text is present, return an empty string."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=120) as client:
        response = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def OCR_TEXT(crop: Image.Image) -> str:
    if settings.development_mode:
        return "[placeholder text from development mode OCR]"

    errors: list[str] = []
    try:
        import pytesseract

        text = pytesseract.image_to_string(crop, lang="eng+jpn+kor", config="--psm 6")
        if text.strip():
            return text.strip()
        errors.append("Tesseract returned no text.")
    except Exception as exc:
        errors.append(f"Tesseract failed: {exc}")

    if settings.gemini_api_key:
        try:
            text = _ocr_with_gemini(crop)
            if text:
                return text
            errors.append("Gemini OCR returned no text.")
        except Exception as exc:
            errors.append(f"Gemini OCR failed: {exc}")

    if settings.openai_api_key:
        try:
            text = _ocr_with_openai(crop)
            if text:
                return text
            errors.append("OpenAI OCR returned no text.")
        except Exception as exc:
            errors.append(f"OpenAI OCR failed: {exc}")

    raise RuntimeError("OCR is unavailable. " + " ".join(errors))


def extract_bubble_texts(image_path: Path, bubbles: List[dict]) -> List[OCRResult]:
    image = Image.open(image_path).convert("RGB")
    results = []
    for index, bubble in enumerate(bubbles):
        x, y, w, h = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
        crop = image.crop((x, y, x + w, y + h))
        text = OCR_TEXT(crop)
        results.append(
            {
                "bubble_index": index,
                "original_text": text,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )
    return results
