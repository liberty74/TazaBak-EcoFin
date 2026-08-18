"""Illegal-dump analysis of a single uploaded frame."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VisionFrame
from app.schemas import DEVICE_ID_PATTERN, VisionResponse
from app.services.camera_vision import (
    classify_illegal_dump,
    record_illegal_dump_alert,
)
from app.services.files import (
    InvalidImageError,
    remove_stored_image,
    save_image_upload,
)
from app.services.device_activity import (
    DeviceInactiveError,
    ensure_municipal_device_is_active,
)
from app.services.telemetry import DeviceKindConflictError, get_or_create_device
from app.services.yolo import YoloAnalysisError, detect_objects


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/frame", response_model=VisionResponse)
async def analyze_vision_frame(
    image: Annotated[UploadFile, File(description="JPEG, PNG or WebP frame")],
    device_id: Annotated[
        str, Form(pattern=DEVICE_ID_PATTERN)
    ] = "municipal-demo-001",
    db: Session = Depends(get_db),
) -> VisionResponse:
    """Analyse one pushed frame for waste dumped outside the container.

    The same weights and the same rule decide here as in the ESP32-CAM polling
    worker: a pushed frame and a captured frame must never disagree about the
    same picture. The upload itself is stored byte for byte, because it is the
    evidence behind the alert — boxes are drawn from ``detected_objects``.
    """

    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=409, detail="Device is inactive") from exc

    try:
        stored = await save_image_upload(image, "vision")
    except InvalidImageError as exc:
        http_status = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if "exceeds" in str(exc)
            else status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )
        logger.warning("Rejected vision upload device=%s: %s", device_id, exc)
        raise HTTPException(status_code=http_status, detail=str(exc)) from exc
    except OSError as exc:
        logger.exception("Could not save vision frame for device=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Frame could not be stored",
        ) from exc

    # Inference is CPU-bound and synchronous; keep it off the event loop.
    try:
        detections = await run_in_threadpool(detect_objects, stored.absolute_path)
    except YoloAnalysisError as exc:
        remove_stored_image(stored)
        logger.exception("YOLO is unavailable for device=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image analysis service is unavailable",
        ) from exc

    illegal_dump, triggers = classify_illegal_dump(detections)
    confidence = max((item.confidence for item in triggers), default=None)
    serialized = [item.to_dict() for item in detections]

    try:
        device = get_or_create_device(db, device_id, "municipal")
        alert = (
            record_illegal_dump_alert(
                db, device, stored.relative_path, serialized, confidence
            )
            if illegal_dump
            else None
        )

        frame = VisionFrame(
            device_id=device.id,
            image_path=stored.relative_path,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            detected=illegal_dump,
            confidence=confidence,
            detections=serialized,
            alert_id=alert.id if alert is not None else None,
        )
        db.add(frame)
        db.commit()
        db.refresh(frame)
    except (DeviceKindConflictError, DeviceInactiveError) as exc:
        db.rollback()
        remove_stored_image(stored)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        remove_stored_image(stored)
        logger.exception("Vision transaction failed for device=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vision result could not be persisted",
        ) from exc

    logger.info(
        "Vision frame processed device=%s detected=%s objects=%s frame_id=%s",
        device_id,
        frame.detected,
        len(detections),
        frame.id,
    )
    return VisionResponse(
        frame_id=frame.id,
        device_id=device_id,
        detected=frame.detected,
        object_label="illegal_dump" if frame.detected else None,
        confidence=frame.confidence,
        detected_objects=serialized,
        alert_id=frame.alert_id,
        image_url=stored.public_url,
    )
