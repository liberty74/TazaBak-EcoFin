"""Replaceable mock for municipal illegal-dump vision detection."""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True, slots=True)
class VisionMockResult:
    detected: bool
    confidence: float | None


def detect_illegal_dump(force_detect: bool = False) -> VisionMockResult:
    detected = force_detect or random.random() < settings.vision_detection_probability
    confidence = round(random.uniform(0.82, 0.98), 4) if detected else None
    return VisionMockResult(detected=detected, confidence=confidence)
