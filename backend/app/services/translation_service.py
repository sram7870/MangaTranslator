"""Translation service: Gemini first, OpenAI fallback, local dev mode."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .translation_memory import TranslationMemory
from ..config import settings

TranslationResult = dict
_translation_memory = TranslationMemory()

# ---------------------------------------------------------------------------
# Local fallbacks (dev mode / no API keys)
# ---------------------------------------------------------------------------

_FALLBACK_MAP: dict[str, str] = {
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


def _local_translate(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    for src, tgt in _FALLBACK_MAP.items():
        if normalized == src:
            return tgt
        if src in normalized:
            return normalized.replace(src, tgt)
    return normalized  # return as-is if nothing matched


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Any:
    """Extract JSON from a response that may contain markdown fences or preamble."""
    # Strip ```json ... ``` fences
    raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to extract first array or object
    for start_ch, end_ch in [("[", "]"), ("{", "}")]:
        start = raw.find(start_ch)
        end = raw.rfind(end_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start: end + 1])
            except json.JSONDecodeError:
                pass

    raise ValueError(f"No valid JSON found in response: {raw[:200]}")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _batch_prompt(items: list[dict], context: str | None, glossary: list[dict] | None) -> str:
    glossary_str = json.dumps(glossary or [], ensure_ascii=False)
    items_str = json.dumps(items, ensure_ascii=False)
    return (
        "You are an expert manga/manhwa translator. Translate the speech bubble texts to "
        "natural English. Return ONLY a JSON array with no extra text, preamble, or markdown. "
        "Each element must have exactly two keys: \"bubble_index\" (integer) and \"translated_text\" (string).\n"
        f"Story context: {context or 'None'}\n"
        f"Glossary terms to keep consistent: {glossary_str}\n"
        f"Bubbles to translate: {items_str}"
    )


def _context_prompt(texts: list[str]) -> str:
    joined = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts) if t.strip())
    return (
        "You are an expert manga/manhwa translation assistant. Analyse these speech bubble texts "
        "and return ONLY a JSON object with no extra text, preamble, or markdown fences.\n"
        "Required shape:\n"
        "{\n"
        '  "summary": "2-3 sentence story/scene summary",\n'
        '  "tone": "translation tone guide (e.g. casual, formal, shounen action)",\n'
        '  "characters": [\n'
        '    {"original": "name in source language", "translated": "English name", '
        '"description": "brief note", "first_seen_page": 1}\n'
        "  ],\n"
        '  "glossary": [\n'
        '    {"original": "term", "translated": "English term", '
        '"category": "character|technique|organization|place|general"}\n'
        "  ]\n"
        "}\n"
        f"Text lines:\n{joined}"
    )


# ---------------------------------------------------------------------------
# API callers
# ---------------------------------------------------------------------------

async def _call_gemini(prompt: str, max_tokens: int = 1500) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured.")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            params={"key": settings.gemini_api_key},
            json=payload,
        )
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text.")
    return text


async def _call_openai(prompt: str, max_tokens: int = 1500) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured.")
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": "You are a manga/manhwa translation expert."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def _llm_request(prompt: str, max_tokens: int = 1500) -> str:
    """Route to Gemini → OpenAI → error."""
    if settings.development_mode:
        # In dev mode return a stub so callers don't crash
        return "[]"

    errors: list[str] = []
    if settings.gemini_api_key:
        try:
            return await _call_gemini(prompt, max_tokens)
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    if settings.openai_api_key:
        try:
            return await _call_openai(prompt, max_tokens)
        except Exception as exc:
            errors.append(f"OpenAI: {exc}")

    raise RuntimeError("All LLM providers failed. " + " | ".join(errors))


# ---------------------------------------------------------------------------
# Context / glossary analysis
# ---------------------------------------------------------------------------

def _heuristic_context(texts: list[str]) -> dict:
    """Build a minimal context dict without an LLM."""
    chars: dict[str, dict] = {}
    terms: dict[str, dict] = {}
    for i, text in enumerate(texts, 1):
        for raw in text.replace("\n", " ").split():
            tok = raw.strip(".,!?\"'()[]{}:;-—")
            if len(tok) < 2:
                continue
            if tok[0].isupper() and tok.isalpha() and len(tok) > 2:
                chars.setdefault(tok, {
                    "original": tok, "translated": tok,
                    "description": "Detected name", "first_seen_page": i,
                })
            elif any(c.isupper() for c in tok[1:]) or "-" in tok:
                terms.setdefault(tok, {
                    "original": tok, "translated": tok, "category": "general",
                })
    return {
        "summary": f"Project has {len([t for t in texts if t.strip()])} speech bubbles.",
        "tone": "Natural, punchy manga English.",
        "characters": list(chars.values())[:20],
        "glossary": list(terms.values())[:40],
    }


async def analyze_story_context(texts: list[str]) -> dict:
    """Return story context dict with summary, tone, characters, glossary."""
    if settings.development_mode or not (settings.gemini_api_key or settings.openai_api_key):
        return _heuristic_context(texts)

    try:
        raw = await _llm_request(_context_prompt(texts), max_tokens=2000)
        payload = _extract_json(raw)
        if not isinstance(payload, dict):
            raise ValueError("Context response is not a JSON object.")
        return {
            "summary": str(payload.get("summary") or ""),
            "tone": str(payload.get("tone") or "Natural manga English."),
            "characters": [c for c in (payload.get("characters") or []) if isinstance(c, dict)],
            "glossary": [g for g in (payload.get("glossary") or []) if isinstance(g, dict)],
        }
    except Exception:
        return _heuristic_context(texts)


# ---------------------------------------------------------------------------
# Batch translation (main pipeline path)
# ---------------------------------------------------------------------------

async def translate_batch(
    items: list[dict],
    context: str | None = None,
    glossary: list[dict] | None = None,
) -> list[TranslationResult]:
    """Translate a batch of {bubble_index, text, page_id} items.

    Returns list of {bubble_index, translated_text, input}.
    Raises RuntimeError if the LLM response is malformed and can't be recovered.
    """
    if not items:
        return []

    results: list[TranslationResult] = []
    uncached: list[dict] = []

    for item in items:
        text = str(item.get("text", ""))
        cached = _translation_memory.get(text)
        if cached is not None:
            results.append({
                "bubble_index": item["bubble_index"],
                "input": text,
                "translated_text": cached,
            })
        else:
            uncached.append(item)

    if not uncached:
        return sorted(results, key=lambda r: r["bubble_index"])

    if settings.development_mode:
        for item in uncached:
            text = str(item.get("text", ""))
            translated = _local_translate(text) or f"[{text[:40]}]"
            _translation_memory.add(text, translated)
            results.append({
                "bubble_index": item["bubble_index"],
                "input": text,
                "translated_text": translated,
            })
        return sorted(results, key=lambda r: r["bubble_index"])

    prompt = _batch_prompt(uncached, context, glossary)
    raw = await _llm_request(prompt, max_tokens=max(1000, len(uncached) * 80))

    parsed = _extract_json(raw)
    if not isinstance(parsed, list):
        raise RuntimeError(f"Batch translation returned non-list JSON: {raw[:300]}")

    by_index: dict[int, str] = {}
    for entry in parsed:
        if isinstance(entry, dict):
            idx = entry.get("bubble_index")
            txt = entry.get("translated_text", "")
            if idx is not None:
                by_index[int(idx)] = str(txt).strip()

    for item in uncached:
        bidx = int(item["bubble_index"])
        text = str(item.get("text", ""))
        translated = by_index.get(bidx)
        if translated is None:
            # Fallback: re-use source text rather than crash
            translated = text
        _translation_memory.add(text, translated)
        results.append({
            "bubble_index": bidx,
            "input": text,
            "translated_text": translated,
        })

    return sorted(results, key=lambda r: r["bubble_index"])


# ---------------------------------------------------------------------------
# Single-text helpers (used by older code paths)
# ---------------------------------------------------------------------------

async def translate_texts(texts: list[str], context: str | None = None) -> list[TranslationResult]:
    items = [{"bubble_index": i, "text": t} for i, t in enumerate(texts)]
    batch = await translate_batch(items, context=context)
    return batch


async def summarize_texts(texts: list[str]) -> str:
    ctx = await analyze_story_context(texts)
    return ctx.get("summary", "")


async def extract_glossary_terms(texts: list[str]) -> list[dict[str, str]]:
    ctx = await analyze_story_context(texts)
    return ctx.get("glossary", [])
