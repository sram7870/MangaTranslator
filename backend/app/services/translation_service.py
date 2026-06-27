from __future__ import annotations

import json
import httpx
from typing import List

from .translation_memory import TranslationMemory
from ..config import settings

TranslationResult = dict
_translation_memory = TranslationMemory()

_FALLBACK_TRANSLATIONS = {
    "こんにちは": "Hello",
    "ありがとう": "Thank you",
    "おはよう": "Good morning",
    "さようなら": "Goodbye",
    "待って": "Wait",
    "行く": "Go",
    "来る": "Come",
    "何": "What",
    "誰": "Who",
    "あなた": "You",
    "私": "I",
    "僕": "I",
    "彼": "He",
    "彼女": "She",
    "今日": "Today",
    "明日": "Tomorrow",
    "今": "Now",
    "いい": "Good",
    "悪い": "Bad",
    "大丈夫": "It's okay",
    "助けて": "Help me",
    "すごい": "Amazing",
    "本当に": "Really",
    "でも": "But",
    "だから": "So",
    "そして": "And",
}


def _use_gemini() -> bool:
    return bool(settings.gemini_api_key)


def _fallback_translate(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""

    lowered = normalized.lower()
    for source, translated in _FALLBACK_TRANSLATIONS.items():
        if lowered == source.lower():
            return translated
        if source in normalized:
            return normalized.replace(source, translated)

    if any(ord(char) > 127 for char in normalized):
        return f"{normalized}"
    return normalized


def _build_prompt(text: str, context: str | None = None) -> str:
    prompt_lines = [
        "Translate the following manga/manhwa speech bubble text into natural English.",
        "Preserve the tone, keep it concise, and make it read like a polished translated comic line.",
        "Do not include the original text in your output.",
    ]
    if context:
        prompt_lines.append(f"Story context: {context}")
    prompt_lines.append(f"Text: {text}")
    return "\n".join(prompt_lines)


def _build_summary_prompt(texts: List[str]) -> str:
    joined = "\n".join(f"- {text}" for text in texts if text.strip())
    return (
        "You are a manga translation assistant. Given the extracted speech bubble text from a comic, "
        "write a short story summary and a translation tone guide for the translator. "
        "Keep it under 3 sentences and focus on characters, emotions, and scene mood.\n"
        f"Text lines:\n{joined}"
    )


def _build_glossary_prompt(texts: List[str]) -> str:
    joined = "\n".join(f"- {text}" for text in texts if text.strip())
    return (
        "You are a manga translation assistant. Extract character names, recurring terms, or proper nouns "
        "that should appear in a project glossary. Respond with valid JSON as an array of objects, "
        "each containing original, translated, and category fields. If none, return an empty list.\n"
        f"Text lines:\n{joined}"
    )


def _build_context_prompt(texts: List[str]) -> str:
    joined = "\n".join(f"{index + 1}. {text}" for index, text in enumerate(texts) if text.strip())
    return (
        "Analyze these manga/manhwa OCR text lines and return valid JSON only with this shape:\n"
        "{"
        "\"summary\":\"short story/context summary\","
        "\"characters\":[{\"original\":\"name\",\"translated\":\"English name\",\"description\":\"short note\",\"first_seen_page\":1}],"
        "\"glossary\":[{\"original\":\"term\",\"translated\":\"English term\",\"category\":\"character|technique|organization|place|general\"}],"
        "\"tone\":\"translation tone guide\""
        "}\n"
        "Prefer consistency and include recurring names, attacks, organizations, places, titles, and cultural terms.\n"
        f"Text lines:\n{joined}"
    )


def _build_batch_translation_prompt(items: list[dict], context: str | None = None, glossary: list[dict] | None = None) -> str:
    return (
        "Translate these manga/manhwa speech bubble OCR lines into natural English. "
        "Return valid JSON only as an array of objects with bubble_index and translated_text. "
        "Keep each line concise enough to fit back into its bubble.\n"
        f"Story context: {context or 'None'}\n"
        f"Glossary: {json.dumps(glossary or [], ensure_ascii=False)}\n"
        f"Bubbles: {json.dumps(items, ensure_ascii=False)}"
    )


async def _call_openai(prompt: str) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI fallback requests.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": "You are a manga translation assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


async def _call_gemini(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini requests.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=headers, params={"key": settings.gemini_api_key}, json=payload)
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini did not return any candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return text


async def _llm_request(prompt: str) -> str:
    if settings.development_mode:
        return _fallback_translate(prompt.split("Text:", 1)[-1].strip())

    provider_errors: list[str] = []
    if _use_gemini():
        try:
            return await _call_gemini(prompt)
        except Exception as exc:
            provider_errors.append(f"Gemini failed: {exc}")
    if settings.openai_api_key:
        try:
            return await _call_openai(prompt)
        except Exception as exc:
            provider_errors.append(f"OpenAI failed: {exc}")
    if provider_errors:
        raise RuntimeError("; ".join(provider_errors))
    raise RuntimeError("No translation provider configured. Set GEMINI_API_KEY or OPENAI_API_KEY.")


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def _heuristic_context(texts: List[str]) -> dict:
    terms: dict[str, dict[str, str]] = {}
    characters: dict[str, dict[str, str | int | None]] = {}
    for index, text in enumerate(texts, start=1):
        for raw_token in text.replace("\n", " ").split():
            token = raw_token.strip(".,!?\"'()[]{}:;")
            if len(token) < 3:
                continue
            if token[:1].isupper() and token.isalpha():
                characters.setdefault(
                    token,
                    {
                        "original": token,
                        "translated": token,
                        "description": "Detected recurring capitalized name or title.",
                        "first_seen_page": index,
                    },
                )
            elif any(char.isupper() for char in token[1:]) or "-" in token:
                terms.setdefault(token, {"original": token, "translated": token, "category": "general"})
    return {
        "summary": f"Project contains {len([text for text in texts if text.strip()])} extracted speech bubble lines.",
        "characters": list(characters.values())[:20],
        "glossary": list(terms.values())[:40],
        "tone": "Natural, concise manga/manhwa English.",
    }


def _validate_context_payload(payload) -> dict:
    if not isinstance(payload, dict):
        return _heuristic_context([])
    characters = payload.get("characters") if isinstance(payload.get("characters"), list) else []
    glossary = payload.get("glossary") if isinstance(payload.get("glossary"), list) else []
    return {
        "summary": str(payload.get("summary") or payload.get("tone") or "No summary available."),
        "characters": [item for item in characters if isinstance(item, dict)],
        "glossary": [item for item in glossary if isinstance(item, dict)],
        "tone": str(payload.get("tone") or "Natural, concise manga/manhwa English."),
    }


async def analyze_story_context(texts: List[str]) -> dict:
    if settings.development_mode:
        return _heuristic_context(texts)
    response = await _llm_request(_build_context_prompt(texts))
    try:
        return _validate_context_payload(_parse_json(response))
    except json.JSONDecodeError:
        return _heuristic_context(texts)


async def translate_texts(texts: List[str], context: str | None = None) -> List[TranslationResult]:
    translations = []
    for text in texts:
        cached = _translation_memory.get(text)
        if cached:
            translations.append({"input": text, "translated_text": cached})
            continue
        translation = await _llm_request(_build_prompt(text, context))
        _translation_memory.add(text, translation)
        translations.append({"input": text, "translated_text": translation})
    return translations


async def translate_batch(items: list[dict], context: str | None = None, glossary: list[dict] | None = None) -> list[TranslationResult]:
    if not items:
        return []

    translations: list[TranslationResult] = []
    uncached_items: list[dict] = []
    for item in items:
        text = str(item.get("text", ""))
        cached = _translation_memory.get(text)
        if cached:
            translations.append({"bubble_index": item["bubble_index"], "input": text, "translated_text": cached})
        else:
            uncached_items.append(item)

    if uncached_items:
        if settings.development_mode:
            parsed = [
                {"bubble_index": item["bubble_index"], "translated_text": _fallback_translate(str(item.get("text", "")))}
                for item in uncached_items
            ]
        else:
            response = await _llm_request(_build_batch_translation_prompt(uncached_items, context, glossary))
            parsed = _parse_json(response)
            if not isinstance(parsed, list):
                raise RuntimeError("Translation provider returned invalid batch JSON.")

        by_index = {int(item.get("bubble_index")): str(item.get("translated_text", "")).strip() for item in parsed if isinstance(item, dict)}
        for item in uncached_items:
            bubble_index = int(item["bubble_index"])
            text = str(item.get("text", ""))
            translated_text = by_index.get(bubble_index)
            if translated_text is None:
                raise RuntimeError(f"Translation provider omitted bubble_index {bubble_index}.")
            _translation_memory.add(text, translated_text)
            translations.append({"bubble_index": bubble_index, "input": text, "translated_text": translated_text})

    return sorted(translations, key=lambda item: item["bubble_index"])


async def summarize_texts(texts: List[str]) -> str:
    if settings.development_mode:
        count = len([text for text in texts if text.strip()])
        return f"Development mode summary for {count} extracted speech bubble(s)."
    prompt = _build_summary_prompt(texts)
    return await _llm_request(prompt)


async def extract_glossary_terms(texts: List[str]) -> list[dict[str, str]]:
    if settings.development_mode:
        return []
    prompt = _build_glossary_prompt(texts)
    response = await _llm_request(prompt)
    try:
        result = _parse_json(response)
    except json.JSONDecodeError:
        return []
    if not isinstance(result, list):
        return []
    return [item for item in result if isinstance(item, dict)]
