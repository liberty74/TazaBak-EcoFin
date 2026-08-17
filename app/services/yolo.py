"""Lazy, thread-safe Ultralytics YOLOv8 inference adapter."""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from app.config import settings


logger = logging.getLogger(__name__)


class YoloAnalysisError(RuntimeError):
    """Raised when model loading or inference is unavailable."""


@dataclass(frozen=True, slots=True)
class DetectedObject:
    label: str
    confidence: float
    bounding_box: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_model: Any | None = None
_model_load_lock = threading.Lock()
_inference_lock = threading.Lock()


def _get_model() -> Any:
    global _model
    if _model is not None:
        return _model
    with _model_load_lock:
        if _model is not None:
            return _model
        try:
            from ultralytics import YOLO

            logger.info("Loading Ultralytics model=%s", settings.yolo_model_path)
            _model = YOLO(settings.yolo_model_path)
        except Exception as exc:
            logger.exception("Could not load YOLO model=%s", settings.yolo_model_path)
            raise YoloAnalysisError("YOLO model is unavailable") from exc
    return _model


def detect_objects(image_path: Path) -> list[DetectedObject]:
    """Run YOLOv8n and return JSON-safe COCO detections."""

    model = _get_model()
    try:
        # The model/predictor keeps mutable state; serialize inference per process.
        with _inference_lock:
            results = model.predict(
                source=str(image_path),
                conf=settings.yolo_confidence,
                device=settings.yolo_device,
                verbose=False,
            )
    except Exception as exc:
        logger.exception("YOLO inference failed image=%s", image_path)
        raise YoloAnalysisError("YOLO inference failed") from exc

    if not results:
        return []

    result = results[0]
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    names = result.names
    detections: list[DetectedObject] = []
    rows = boxes.data.cpu().tolist()
    for row in rows:
        if len(row) < 6:
            continue
        x1, y1, x2, y2, confidence, class_id = row[:6]
        label = str(names.get(int(class_id), int(class_id))).casefold()
        detections.append(
            DetectedObject(
                label=label,
                confidence=round(float(confidence), 5),
                bounding_box=[
                    round(float(x1), 2),
                    round(float(y1), 2),
                    round(float(x2), 2),
                    round(float(y2), 2),
                ],
            )
        )
    detections.sort(key=lambda item: item.confidence, reverse=True)
    return detections


def save_annotated_image(
    source_path: Path,
    destination_path: Path,
    detections: list[DetectedObject],
    *,
    illegal_dump: bool,
) -> None:
    """Render YOLO boxes and a clear/danger banner into a JPEG evidence frame."""

    with Image.open(source_path) as source:
        image = source.convert("RGB")

    draw = ImageDraw.Draw(image)
    line_width = max(2, round(min(image.size) / 180))
    for detection in detections:
        x1, y1, x2, y2 = detection.bounding_box
        color = "#ff3b30" if illegal_dump else "#22c55e"
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
        label = f"{detection.label} {detection.confidence:.0%}"
        text_box = draw.textbbox((x1, y1), label)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        label_top = max(0, y1 - text_height - 8)
        draw.rectangle(
            (x1, label_top, x1 + text_width + 8, label_top + text_height + 8),
            fill=color,
        )
        draw.text((x1 + 4, label_top + 4), label, fill="white")

    banner = "ILLEGAL DUMP DETECTED" if illegal_dump else "AREA CLEAR"
    banner_color = "#dc2626" if illegal_dump else "#15803d"
    banner_box = draw.textbbox((0, 0), banner)
    banner_width = banner_box[2] - banner_box[0]
    banner_height = banner_box[3] - banner_box[1]
    draw.rounded_rectangle(
        (12, 12, 28 + banner_width, 28 + banner_height),
        radius=6,
        fill=banner_color,
    )
    draw.text((20, 20), banner, fill="white")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination_path, format="JPEG", quality=88, optimize=True)


def classify_detections(
    detections: list[DetectedObject],
) -> tuple[str, str | None]:
    labels = {detection.label.casefold() for detection in detections}
    mold_classes = {label.casefold() for label in settings.yolo_mold_classes}
    bread_classes = {label.casefold() for label in settings.yolo_bread_classes}
    if labels & mold_classes:
        return "reject", "mold_detected"
    if labels & bread_classes:
        return "approve", None
    return "invalid", "not_bread"
