"""ESP32-CAM illegal-dump analysis endpoint."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, VisionFrame
from app.schemas import DEVICE_ID_PATTERN, VisionResponse
from app.services.ai_mocks import detect_illegal_dump
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


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/frame", response_model=VisionResponse)
async def analyze_vision_frame(
    image: Annotated[UploadFile, File(description="JPEG, PNG or WebP frame")],
    device_id: Annotated[
        str, Form(pattern=DEVICE_ID_PATTERN)
    ] = "municipal-demo-001",
    force_detect: Annotated[
        bool, Form(description="Deterministic demo trigger")
    ] = True,
    db: Session = Depends(get_db),
) -> VisionResponse:
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

    try:
        device = get_or_create_device(db, device_id, "municipal")
        result = detect_illegal_dump(force_detect=force_detect)
        alert: Alert | None = None
        if result.detected:
            alert = Alert(
                device_id=device.id,
                alert_type="ILLEGAL_DUMP",
                status="CRITICAL",
                message="Computer-vision mock detected waste outside the container",
                evidence_path=stored.relative_path,
                details={"confidence": result.confidence, "model": "mock-cv-v1"},
            )
            db.add(alert)
            db.flush()

        frame = VisionFrame(
            device_id=device.id,
            image_path=stored.relative_path,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            detected=result.detected,
            confidence=result.confidence,
            alert_id=alert.id if alert else None,
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
        "Vision frame processed device=%s detected=%s frame_id=%s",
        device_id,
        frame.detected,
        frame.id,
    )
    return VisionResponse(
        frame_id=frame.id,
        device_id=device_id,
        detected=frame.detected,
        object_label="illegal_dump" if frame.detected else None,
        confidence=frame.confidence,
        alert_id=frame.alert_id,
        image_url=stored.public_url,
    )
