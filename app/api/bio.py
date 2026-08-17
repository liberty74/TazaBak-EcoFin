"""YOLOv8-powered, idempotent bread quality analysis endpoint."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Alert, BioAnalysis, Device, DeviceCommand, User, utcnow
from app.schemas import BioResponse, DEVICE_ID_PATTERN
from app.services.commands import record_delivery
from app.services.device_locks import serialize_device
from app.services.files import InvalidImageError, remove_stored_image, save_image_upload
from app.services.points import credit_points
from app.services.telemetry import DeviceKindConflictError, get_or_create_device
from app.services.users import find_user
from app.services.websocket import send_device_command
from app.services.yolo import YoloAnalysisError, classify_detections, detect_objects


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bio", tags=["bio"])


def _unique_qr_code(db: Session, prefix: str) -> str:
    for _ in range(20):
        code = f"{prefix}{secrets.randbelow(900_000) + 100_000}"
        exists = db.scalar(
            select(BioAnalysis.id).where(BioAnalysis.qr_code == code).limit(1)
        )
        if exists is None:
            return code
    raise RuntimeError("Could not allocate a unique QR code")


def _status_metadata(
    analysis_status: str,
) -> tuple[str, int, Literal["mold_detected", "not_bread"] | None]:
    if analysis_status == "approve":
        return "GOOD", settings.bio_reward_points, None
    if analysis_status == "reject":
        return "BAD", 0, "mold_detected"
    return "NONE", 0, "not_bread"


def _unresolved_fire_exists(db: Session, device_id: str) -> bool:
    return (
        db.scalar(
            select(Alert.id)
            .where(
                Alert.device_id == device_id,
                Alert.alert_type == "FIRE_RISK",
                Alert.is_resolved.is_(False),
            )
            .limit(1)
        )
        is not None
    )


def _assert_bio_device_is_safe(db: Session, device_id: str) -> None:
    device = db.get(Device, device_id)
    if device is not None and device.kind != "bio":
        raise HTTPException(
            status_code=409,
            detail=f"Device {device_id!r} is registered as {device.kind}, not bio",
        )
    if _unresolved_fire_exists(db, device_id):
        raise HTTPException(
            status_code=409,
            detail="Bread analysis is blocked while FIRE_RISK is unresolved",
        )


def _response_for_analysis(
    db: Session,
    analysis: BioAnalysis,
    current_balance: int,
) -> BioResponse:
    command = db.scalar(
        select(DeviceCommand).where(
            DeviceCommand.idempotency_key == f"bio-analysis:{analysis.id}"
        )
    )
    command_is_active = command is not None and command.status in {
        "PENDING",
        "SENT",
        "ACKED",
    }
    return BioResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        qr_code=analysis.qr_code,
        points_awarded=analysis.points,
        current_balance=current_balance,
        detected_objects=analysis.detected_objects,
        user_id=analysis.user_id,
        image_url=(
            f"/static/{analysis.image_path}" if analysis.image_path is not None else None
        ),
        command_sent=command is not None and command.status in {"SENT", "ACKED"},
        action_triggered="OPEN_LID"
        if analysis.status == "approve" and command_is_active
        else None,
        reason=analysis.reason,
    )


def _persist_empty_analysis(
    db: Session,
    *,
    user_id: int,
    device_id: str,
    operation_key: str,
) -> BioAnalysis:
    device = get_or_create_device(db, device_id, "bio")
    analysis = BioAnalysis(
        device_id=device.id,
        user_id=user_id,
        image_path=None,
        image_sha256=None,
        status="invalid",
        points=0,
        reason="empty_frame",
        qr_code=_unique_qr_code(db, "NONE"),
        idempotency_key=operation_key,
        detected_objects=[],
        model_name=settings.yolo_model_path,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/analyze", response_model=BioResponse)
async def analyze_bio_image(
    file: Annotated[UploadFile, File(description="Bread image")],
    user_id: Annotated[str, Form(min_length=1, max_length=64)],
    device_id: Annotated[str, Form(pattern=DEVICE_ID_PATTERN)] = "bio-demo-001",
    idempotency_key: Annotated[
        str | None, Form(min_length=8, max_length=64)
    ] = None,
    db: Session = Depends(get_db),
) -> BioResponse:
    """Classify an upload and atomically award points exactly once."""

    user = find_user(db, user_id)
    if user is None:
        await file.close()
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "dispatcher":
        await file.close()
        raise HTTPException(status_code=403, detail="Dispatcher cannot submit bread")
    resolved_user_id = user.id
    try:
        _assert_bio_device_is_safe(db, device_id)
    except HTTPException:
        await file.close()
        raise
    # Do not keep request-scoped reads open across upload I/O or model inference.
    db.rollback()

    try:
        stored = await save_image_upload(file, "bio")
    except InvalidImageError as exc:
        if "empty" in str(exc).casefold():
            user = db.get(User, resolved_user_id)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found") from exc
            _assert_bio_device_is_safe(db, device_id)
            operation_key = (
                f"bio:{resolved_user_id}:{device_id}:client:{idempotency_key}"
                if idempotency_key is not None
                else f"bio:{resolved_user_id}:{device_id}:empty:{secrets.token_hex(16)}"
            )
            existing = db.scalar(
                select(BioAnalysis).where(
                    BioAnalysis.idempotency_key == operation_key
                )
            )
            if existing is not None:
                return _response_for_analysis(db, existing, user.points)
            try:
                analysis = _persist_empty_analysis(
                    db,
                    user_id=resolved_user_id,
                    device_id=device_id,
                    operation_key=operation_key,
                )
            except (SQLAlchemyError, RuntimeError, DeviceKindConflictError):
                db.rollback()
                logger.exception("Could not persist empty bio analysis")
                raise HTTPException(
                    status_code=500, detail="Analysis result could not be persisted"
                ) from exc
            return _response_for_analysis(db, analysis, user.points)
        http_status = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if "exceeds" in str(exc)
            else status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )
        logger.warning("Rejected bio upload device=%s: %s", device_id, exc)
        raise HTTPException(status_code=http_status, detail=str(exc)) from exc
    except OSError as exc:
        logger.exception("Could not save bio image for device=%s", device_id)
        raise HTTPException(status_code=500, detail="Image could not be stored") from exc

    operation_key = (
        f"bio:{resolved_user_id}:{device_id}:client:{idempotency_key}"
        if idempotency_key is not None
        else f"bio:{resolved_user_id}:{device_id}:sha256:{stored.sha256_hex}"
    )
    existing = db.scalar(
        select(BioAnalysis).where(BioAnalysis.idempotency_key == operation_key)
    )
    if existing is not None:
        if existing.image_sha256 != stored.sha256_hex:
            remove_stored_image(stored)
            raise HTTPException(status_code=409, detail="Idempotency key conflict")
        remove_stored_image(stored)
        replay_user = db.get(User, resolved_user_id)
        return _response_for_analysis(
            db, existing, replay_user.points if replay_user is not None else 0
        )

    db.rollback()

    try:
        detections = await run_in_threadpool(detect_objects, stored.absolute_path)
    except YoloAnalysisError as exc:
        remove_stored_image(stored)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image analysis service is unavailable",
        ) from exc

    analysis_status, _ = classify_detections(detections)
    qr_prefix, points, reason = _status_metadata(analysis_status)
    detection_payload = [detected.to_dict() for detected in detections]
    command: DeviceCommand | None = None

    try:
        user = db.get(User, resolved_user_id)
        if user is None:
            remove_stored_image(stored)
            raise HTTPException(status_code=404, detail="User not found")
        if user.role == "dispatcher":
            remove_stored_image(stored)
            raise HTTPException(status_code=403, detail="Dispatcher cannot submit bread")
        _assert_bio_device_is_safe(db, device_id)
        replay = db.scalar(
            select(BioAnalysis).where(
                BioAnalysis.idempotency_key == operation_key
            )
        )
        if replay is not None:
            if replay.image_sha256 != stored.sha256_hex:
                remove_stored_image(stored)
                raise HTTPException(status_code=409, detail="Idempotency key conflict")
            remove_stored_image(stored)
            return _response_for_analysis(db, replay, user.points)

        device = get_or_create_device(db, device_id, "bio")
        analysis = BioAnalysis(
            device_id=device.id,
            user_id=user.id,
            image_path=stored.relative_path,
            image_sha256=stored.sha256_hex,
            status=analysis_status,
            points=points,
            reason=reason,
            qr_code=_unique_qr_code(db, qr_prefix),
            idempotency_key=operation_key,
            detected_objects=detection_payload,
            model_name=settings.yolo_model_path,
        )
        db.add(analysis)
        db.flush()

        balance = user.points
        if analysis_status == "approve":
            points_result = credit_points(
                db,
                user,
                settings.bio_reward_points,
                "BIO_REWARD",
                "Начисление за качественный хлеб",
                f"bio:{analysis.id}",
            )
            balance = points_result.balance
            command = DeviceCommand(
                device_id=device_id,
                action="OPEN_LID",
                requested_by_id=user.id,
                idempotency_key=f"bio-analysis:{analysis.id}",
                payload={},
                expires_at=utcnow() + timedelta(seconds=30),
            )
            db.add(command)
            db.flush()
            command.payload = {
                "action": "OPEN_LID",
                "command_id": command.id,
                "analysis_id": analysis.id,
            }
            device.lid_status = "OPEN_REQUESTED"

        db.commit()
        db.refresh(analysis)
    except HTTPException:
        db.rollback()
        remove_stored_image(stored)
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(BioAnalysis).where(BioAnalysis.idempotency_key == operation_key)
        )
        if replay is not None and replay.image_sha256 == stored.sha256_hex:
            remove_stored_image(stored)
            refreshed_user = db.get(type(user), user.id)
            return _response_for_analysis(
                db, replay, refreshed_user.points if refreshed_user is not None else 0
            )
        remove_stored_image(stored)
        logger.exception("Bio idempotency conflict device=%s", device_id)
        raise HTTPException(status_code=409, detail="Idempotency key conflict") from exc
    except (SQLAlchemyError, RuntimeError, ValueError, DeviceKindConflictError) as exc:
        db.rollback()
        remove_stored_image(stored)
        logger.exception("Bio transaction failed for device=%s", device_id)
        raise HTTPException(
            status_code=500, detail="Analysis result could not be persisted"
        ) from exc

    command_sent = False
    action_triggered: Literal["OPEN_LID"] | None = None
    if analysis_status == "approve" and command is not None:
        async with serialize_device(device_id):
            db.refresh(command)
            if command.status in {"SENT", "ACKED"}:
                action_triggered = "OPEN_LID"
                command_sent = True
            elif _unresolved_fire_exists(db, device_id):
                command.status = "FAILED"
                command.last_error = "blocked_by_fire_interlock"
                db.commit()
                logger.critical(
                    "Blocked Bio OPEN_LID because fire alert appeared device=%s",
                    device_id,
                )
            elif command.status == "PENDING":
                action_triggered = "OPEN_LID"
                command_sent = await send_device_command(
                    device_id, dict(command.payload)
                )
                try:
                    record_delivery(db, command.id, command_sent)
                except SQLAlchemyError:
                    db.rollback()
                    logger.exception("Could not persist OPEN_LID delivery state")

    logger.info(
        "Bio analysis completed device=%s status=%s analysis_id=%s detections=%s",
        device_id,
        analysis_status,
        analysis.id,
        len(detections),
    )
    return BioResponse(
        analysis_id=analysis.id,
        status=analysis_status,
        qr_code=analysis.qr_code,
        points_awarded=points,
        current_balance=balance,
        detected_objects=detection_payload,
        user_id=user.id,
        image_url=stored.public_url,
        command_sent=command_sent,
        action_triggered=action_triggered,
        reason=reason,
    )
