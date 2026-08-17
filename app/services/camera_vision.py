"""Automatic ESP32-CAM snapshot analysis and illegal-dump alerting."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import requests
from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Alert, BinContainer, Device, VisionFrame, utcnow
from app.services.device_activity import (
    DeviceInactiveError,
    ensure_municipal_device_is_active,
)
from app.services.yolo import DetectedObject, detect_objects, save_annotated_image


logger = logging.getLogger(__name__)

# Large road objects and people are normal background around a municipal bin.
# They do not participate in the generic "several objects" trigger.
BACKGROUND_CLASSES = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
}


class CameraAnalysisError(RuntimeError):
    """Raised when a configured camera cannot provide an analyzable frame."""


def capture_url_from_stream(stream_url: str) -> str:
    """Convert the standard ESP32 CameraWebServer MJPEG URL to `/capture`."""

    parsed = urlsplit(stream_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CameraAnalysisError("Camera stream URL is invalid")

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = parsed.port
    # The official example exposes control/capture on :80 and MJPEG on :81.
    if parsed.scheme == "http" and port == 81:
        port = None
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((parsed.scheme, netloc, "/capture", "", ""))


def _download_snapshot(capture_url: str, destination: Path) -> None:
    """Download one bounded, decoded image from an ESP32-CAM."""

    try:
        with requests.get(
            capture_url,
            stream=True,
            timeout=(2, settings.camera_capture_timeout_seconds),
        ) as response:
            response.raise_for_status()
            size = 0
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise CameraAnalysisError("Camera snapshot exceeds upload limit")
                    output.write(chunk)
    except requests.RequestException as exc:
        raise CameraAnalysisError(f"ESP32-CAM capture is unavailable: {exc}") from exc

    if destination.stat().st_size == 0:
        raise CameraAnalysisError("ESP32-CAM returned an empty snapshot")
    try:
        with Image.open(destination) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise CameraAnalysisError("Camera snapshot dimensions are invalid")
            if width * height > settings.max_image_pixels:
                raise CameraAnalysisError("Camera snapshot exceeds pixel limit")
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise CameraAnalysisError("ESP32-CAM returned an invalid image") from exc


def _download_snapshot_from_mjpeg(stream_url: str, destination: Path) -> None:
    """Extract one JPEG from MJPEG when a firmware has no `/capture` route."""

    buffer = bytearray()
    try:
        with requests.get(
            stream_url,
            stream=True,
            timeout=(2, settings.camera_capture_timeout_seconds),
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=16 * 1024):
                if not chunk:
                    continue
                buffer.extend(chunk)
                start = buffer.find(b"\xff\xd8")
                if start > 0:
                    del buffer[:start]
                    start = 0
                if start == 0:
                    end = buffer.find(b"\xff\xd9", 2)
                    if end >= 0:
                        destination.write_bytes(buffer[: end + 2])
                        break
                if len(buffer) > settings.max_upload_bytes:
                    raise CameraAnalysisError("MJPEG frame exceeds upload limit")
    except requests.RequestException as exc:
        raise CameraAnalysisError(f"ESP32-CAM MJPEG stream is unavailable: {exc}") from exc

    if not destination.exists() or destination.stat().st_size == 0:
        raise CameraAnalysisError("MJPEG stream returned no complete JPEG frame")
    try:
        with Image.open(destination) as image:
            width, height = image.size
            if width * height > settings.max_image_pixels:
                raise CameraAnalysisError("Camera snapshot exceeds pixel limit")
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise CameraAnalysisError("MJPEG stream returned an invalid JPEG") from exc


def classify_illegal_dump(
    detections: list[DetectedObject],
) -> tuple[bool, list[DetectedObject]]:
    """Apply the transparent MVP rule on top of COCO object detections."""

    configured = {
        label.casefold() for label in settings.camera_illegal_dump_classes
    }
    explicit_waste = [
        item for item in detections if item.label.casefold() in configured
    ]
    if explicit_waste:
        return True, explicit_waste

    foreground = [
        item
        for item in detections
        if item.label.casefold() not in BACKGROUND_CLASSES
    ]
    return (
        len(foreground) >= settings.camera_illegal_dump_min_objects,
        foreground,
    )


def _latest_or_new_alert(
    db: Session,
    device: Device,
    evidence_path: str,
    detections: list[dict[str, object]],
    confidence: float | None,
) -> Alert | None:
    unresolved = db.scalar(
        select(Alert)
        .where(
            Alert.device_id == device.id,
            Alert.alert_type == "ILLEGAL_DUMP",
            Alert.is_resolved.is_(False),
        )
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    details = {
        "model": Path(settings.yolo_model_path).name,
        "confidence": confidence,
        "detected_objects": detections,
        "rule": "configured waste class or multiple foreground objects",
    }
    if unresolved is not None:
        # Keep one incident open but refresh its evidence with the newest frame.
        unresolved.evidence_path = evidence_path
        unresolved.details = details
        return unresolved

    latest = db.scalar(
        select(Alert)
        .where(
            Alert.device_id == device.id,
            Alert.alert_type == "ILLEGAL_DUMP",
        )
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    if (
        latest is not None
        and settings.camera_alert_cooldown_seconds > 0
        and latest.created_at
        > utcnow() - timedelta(seconds=settings.camera_alert_cooldown_seconds)
    ):
        return None

    alert = Alert(
        device_id=device.id,
        alert_type="ILLEGAL_DUMP",
        status="CRITICAL",
        message="YOLOv8 обнаружил возможный навал мусора возле контейнера",
        evidence_path=evidence_path,
        details=details,
    )
    db.add(alert)
    db.flush()
    return alert


def analyze_camera_device(db: Session, device: Device) -> VisionFrame:
    """Capture, analyze, annotate and persist one frame for a device."""

    if not device.camera_stream_url:
        raise CameraAnalysisError("Camera stream is not configured")

    vision_dir = settings.static_dir / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix="camera-capture-", suffix=".jpg", dir=vision_dir
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    output_path = vision_dir / (
        f"{device.id}-{utcnow():%Y%m%dT%H%M%S}-{uuid4().hex[:8]}.jpg"
    )

    try:
        capture_url = capture_url_from_stream(device.camera_stream_url)
        try:
            _download_snapshot(capture_url, temporary_path)
        except CameraAnalysisError as capture_error:
            logger.warning(
                "Snapshot endpoint unavailable device=%s; trying MJPEG frame: %s",
                device.id,
                capture_error,
            )
            temporary_path.unlink(missing_ok=True)
            _download_snapshot_from_mjpeg(device.camera_stream_url, temporary_path)
        detections = detect_objects(temporary_path)
        illegal_dump, triggers = classify_illegal_dump(detections)
        confidence = max((item.confidence for item in triggers), default=None)
        save_annotated_image(
            temporary_path,
            output_path,
            detections,
            illegal_dump=illegal_dump,
        )
        relative_path = output_path.relative_to(settings.static_dir).as_posix()
        serialized = [item.to_dict() for item in detections]

        alert = None
        if illegal_dump:
            alert = _latest_or_new_alert(
                db,
                device,
                relative_path,
                serialized,
                confidence,
            )

        frame = VisionFrame(
            device_id=device.id,
            image_path=relative_path,
            mime_type="image/jpeg",
            size_bytes=output_path.stat().st_size,
            detected=illegal_dump,
            confidence=confidence,
            detections=serialized,
            alert_id=alert.id if alert is not None else None,
        )
        db.add(frame)

        old_frames = list(
            db.scalars(
                select(VisionFrame)
                .where(VisionFrame.device_id == device.id)
                .order_by(VisionFrame.created_at.desc(), VisionFrame.id.desc())
                .offset(settings.camera_frame_retention - 1)
            ).all()
        )
        protected_evidence_paths = {
            path
            for path in db.scalars(
                select(Alert.evidence_path).where(Alert.evidence_path.is_not(None))
            ).all()
            if path is not None
        }
        old_paths = [
            settings.static_dir / item.image_path
            for item in old_frames
            if item.image_path not in protected_evidence_paths
        ]
        for old_frame in old_frames:
            db.delete(old_frame)

        db.commit()
        db.refresh(frame)
        for old_path in old_paths:
            if old_path != output_path:
                old_path.unlink(missing_ok=True)
        logger.info(
            "Camera frame analyzed device=%s detected=%s objects=%s frame_id=%s",
            device.id,
            illegal_dump,
            len(detections),
            frame.id,
        )
        return frame
    except Exception:
        db.rollback()
        output_path.unlink(missing_ok=True)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)


def analyze_device_by_id(db: Session, device_id: str) -> VisionFrame:
    device = db.get(Device, device_id)
    if device is None:
        raise CameraAnalysisError("Device not found")
    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise CameraAnalysisError("Device is inactive") from exc
    return analyze_camera_device(db, device)


def analyze_all_configured_cameras(
    session_factory: Callable[[], Session],
) -> None:
    with session_factory() as db:
        device_ids = list(
            db.scalars(
                select(Device.id)
                .outerjoin(BinContainer, BinContainer.device_id == Device.id)
                .where(
                    Device.camera_stream_url.is_not(None),
                    or_(BinContainer.id.is_(None), BinContainer.is_active.is_(True)),
                )
            ).all()
        )

    for device_id in device_ids:
        with session_factory() as db:
            try:
                analyze_device_by_id(db, device_id)
            except CameraAnalysisError as exc:
                logger.warning("Camera analysis skipped device=%s: %s", device_id, exc)
            except Exception:
                logger.exception("Camera analysis failed device=%s", device_id)


async def camera_analysis_loop(
    session_factory: Callable[[], Session],
) -> None:
    """Run analysis off the FastAPI event loop until application shutdown."""

    logger.info(
        "ESP32-CAM YOLO worker started interval_seconds=%s",
        settings.camera_analysis_interval_seconds,
    )
    while True:
        started = time.monotonic()
        await asyncio.to_thread(analyze_all_configured_cameras, session_factory)
        elapsed = time.monotonic() - started
        await asyncio.sleep(
            max(0.5, settings.camera_analysis_interval_seconds - elapsed)
        )
