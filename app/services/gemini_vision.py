"""Bread quality classification through Gemini, for machines without models.

CLIP and YOLOv8 need roughly 700 MB of memory between them. A free cloud
instance has 512 MB, so on the public showcase the local path is simply not
installed. Leaving the feature dead there is not acceptable: photographing
bread is the first thing anyone tries.

Gemini is already a dependency of this project and it reads images, so the
same three-way decision can be asked of it over the network at no memory cost.

**This is not the same evidence as CLIP.** CLIP's numbers are a softmax over
cosine similarities — a real distribution the model computes. The numbers here
are what a language model says its confidence is, which is a self-report. Both
are reported under an explicit engine name so a screen never claims the one
while showing the other, and the local path stays primary wherever it exists.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import requests

from app.config import settings
from app.services.clip_bread import (
    PROMPTS,
    BreadClassification,
    BreadDecision,
    ClipAnalysisError,
)


logger = logging.getLogger(__name__)


_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_DECISIONS: tuple[BreadDecision, ...] = tuple(PROMPTS)

# The wording mirrors the CLIP prompts on purpose: both engines are asked to
# separate the same three cases, so their answers stay comparable.
_INSTRUCTION = (
    "Ты классифицируешь фотографию для пункта приёма хлеба. "
    "Реши, что на снимке, и распредели вероятность между тремя вариантами:\n"
    "fresh_bread — свежий, сухой, съедобный хлеб без плесени;\n"
    "moldy_bread — хлеб с плесенью, пятнами, налётом или явной порчей;\n"
    "no_bread — на снимке нет хлеба.\n"
    "Верни только три числа от 0 до 1, в сумме примерно единица. "
    "Не добавляй пояснений."
)

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {decision: {"type": "NUMBER"} for decision in _DECISIONS},
    "required": list(_DECISIONS),
}


def remote_analysis_available() -> bool:
    """Whether a photograph can be judged without local models."""

    return bool(settings.gemini_api_key)


def _mime_type(image_path: Path) -> str:
    return _MIME_BY_SUFFIX.get(image_path.suffix.casefold(), "image/jpeg")


def _normalized(raw: dict[str, object]) -> dict[str, float]:
    """Turn the model's three numbers into a distribution that sums to one.

    A language model asked for probabilities can return 0.9/0.2/0.05. Rescaling
    keeps the ordering it intended while making the numbers on screen add up,
    which is the least surprising thing for whoever reads them.
    """

    values: dict[str, float] = {}
    for decision in _DECISIONS:
        try:
            value = float(raw.get(decision, 0.0))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            value = 0.0
        values[decision] = max(0.0, value)

    total = sum(values.values())
    if total <= 0:
        raise ClipAnalysisError("Remote classifier returned no usable numbers")
    return {key: round(value / total, 4) for key, value in values.items()}


def classify_bread_remote(image_path: Path) -> BreadClassification:
    """Ask Gemini to place one photograph into the three known cases."""

    if not settings.gemini_api_key:
        raise ClipAnalysisError("Remote image analysis is not configured")

    try:
        payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    except OSError as exc:
        raise ClipAnalysisError("Uploaded image could not be read") from exc

    model = settings.gemini_model
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": _INSTRUCTION},
                            {
                                "inline_data": {
                                    "mime_type": _mime_type(image_path),
                                    "data": payload,
                                }
                            },
                        ],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    # Newer Gemini models spend part of the budget on internal
                    # reasoning before the first visible token. A budget sized
                    # for three numbers alone comes back with no text at all.
                    "maxOutputTokens": max(settings.gemini_max_output_tokens, 800),
                    "responseMimeType": "application/json",
                    "responseSchema": _RESPONSE_SCHEMA,
                },
            },
            timeout=settings.gemini_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        logger.warning("Remote bread analysis failed model=%s error=%s", model, exc)
        raise ClipAnalysisError("Remote image analysis failed") from exc

    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Remote bread analysis returned no text body=%s", str(body)[:300])
        raise ClipAnalysisError("Remote classifier returned no readable answer") from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClipAnalysisError("Remote classifier returned malformed JSON") from exc
    if not isinstance(raw, dict):
        raise ClipAnalysisError("Remote classifier returned an unexpected shape")

    probabilities = _normalized(raw)
    decision = max(probabilities, key=probabilities.__getitem__)
    return BreadClassification(
        decision=decision,  # type: ignore[arg-type]
        confidence=probabilities[decision],
        probabilities=probabilities,
        model=model,
        engine="gemini-vision",
    )
