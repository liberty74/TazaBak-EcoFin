"""Role-protected dispatcher device-control endpoints."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, BinContainer, Device, DeviceCommand, Telemetry, VisionFrame
from app.schemas import (
    CameraAnalysisResponse,
    CameraStreamUpdate,
    DeviceCommandResponse,
    DeviceTelemetryStatus,
    DispatcherCommandRequest,
)
from app.security import require_dispatcher_key
from app.services.commands import record_delivery
from app.services.device_activity import (
    DeviceInactiveError,
    ensure_municipal_device_is_active,
)
from app.services.device_locks import device_lock_dependency
from app.services.users import find_user
from app.services.websocket import send_device_command
from app.services.camera_vision import CameraAnalysisError, analyze_device_by_id


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/dispatcher",
    tags=["dispatcher"],
    dependencies=[Depends(require_dispatcher_key)],
)


@router.get("/devices/status", response_model=list[DeviceTelemetryStatus])
def list_device_statuses(db: Session = Depends(get_db)) -> list[DeviceTelemetryStatus]:
    """Return physical lid state, latest DS18B20 readings and camera setup."""

    devices = list(
        db.scalars(
            select(Device)
            .join(BinContainer, BinContainer.device_id == Device.id)
            .where(BinContainer.is_active.is_(True))
            .order_by(Device.id.asc())
        ).all()
    )
    statuses: list[DeviceTelemetryStatus] = []
    for device in devices:
        telemetry = db.scalar(
            select(Telemetry)
            .where(Telemetry.device_id == device.id)
            .order_by(Telemetry.received_at.desc(), Telemetry.id.desc())
            .limit(1)
        )
        statuses.append(
            DeviceTelemetryStatus(
                device_id=device.id,
                lid_status=device.lid_status,
                last_seen_at=device.last_seen_at,
                temperature_in_c=telemetry.temp_in_c if telemetry else None,
                temperature_out_c=telemetry.temp_out_c if telemetry else None,
                temperature_delta_c=telemetry.temperature_delta_c if telemetry else None,
                measured_at=telemetry.measured_at if telemetry else None,
                camera_stream_url=(
                    f"/api/cameras/{device.id}/stream"
                    if device.camera_stream_url
                    else None
                ),
            )
        )
    return statuses


@router.put("/devices/{device_id}/camera", response_model=DeviceTelemetryStatus)
def set_camera_stream(
    device_id: str,
    payload: CameraStreamUpdate,
    db: Session = Depends(get_db),
) -> DeviceTelemetryStatus:
    """Save the LAN MJPEG URL of an ESP32-CAM for FastAPI proxy streaming."""

    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=409, detail="Device is inactive") from exc
    device.camera_stream_url = payload.stream_url
    db.commit()
    db.refresh(device)
    telemetry = db.scalar(
        select(Telemetry)
        .where(Telemetry.device_id == device.id)
        .order_by(Telemetry.received_at.desc(), Telemetry.id.desc())
        .limit(1)
    )
    return DeviceTelemetryStatus(
        device_id=device.id,
        lid_status=device.lid_status,
        last_seen_at=device.last_seen_at,
        temperature_in_c=telemetry.temp_in_c if telemetry else None,
        temperature_out_c=telemetry.temp_out_c if telemetry else None,
        temperature_delta_c=telemetry.temperature_delta_c if telemetry else None,
        measured_at=telemetry.measured_at if telemetry else None,
        camera_stream_url=f"/api/cameras/{device.id}/stream",
    )


def _camera_analysis_response(frame: VisionFrame) -> CameraAnalysisResponse:
    return CameraAnalysisResponse(
        frame_id=frame.id,
        device_id=frame.device_id,
        detected=frame.detected,
        confidence=frame.confidence,
        detected_objects=frame.detections,
        image_url=f"/static/{frame.image_path}",
        alert_id=frame.alert_id,
        created_at=frame.created_at,
    )


@router.get(
    "/devices/{device_id}/camera/analysis",
    response_model=CameraAnalysisResponse,
)
def latest_camera_analysis(
    device_id: str,
    db: Session = Depends(get_db),
) -> CameraAnalysisResponse:
    if db.get(Device, device_id) is None:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=404, detail="Camera is not configured") from exc
    frame = db.scalar(
        select(VisionFrame)
        .where(VisionFrame.device_id == device_id)
        .order_by(VisionFrame.created_at.desc(), VisionFrame.id.desc())
        .limit(1)
    )
    if frame is None:
        raise HTTPException(status_code=404, detail="Camera has not been analyzed yet")
    return _camera_analysis_response(frame)


@router.post(
    "/devices/{device_id}/camera/analyze",
    response_model=CameraAnalysisResponse,
)
def analyze_camera_now(
    device_id: str,
    db: Session = Depends(get_db),
) -> CameraAnalysisResponse:
    """Run one analysis immediately for a deterministic live demo."""

    try:
        frame = analyze_device_by_id(db, device_id)
    except CameraAnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Manual camera analysis failed device=%s", device_id)
        raise HTTPException(
            status_code=500,
            detail="YOLO camera analysis failed",
        ) from exc
    return _camera_analysis_response(frame)


def _response(command: DeviceCommand, command_sent: bool) -> DeviceCommandResponse:
    public_idempotency_key = command.idempotency_key.removeprefix("dispatcher:")
    return DeviceCommandResponse(
        id=command.id,
        device_id=command.device_id,
        action=command.action,
        status=command.status,
        command_sent=command_sent,
        idempotency_key=public_idempotency_key,
        created_at=command.created_at,
    )


@router.post(
    "/devices/{device_id}/command",
    response_model=DeviceCommandResponse,
)
async def issue_device_command(
    device_id: str,
    payload: DispatcherCommandRequest,
    _device_lock: None = Depends(device_lock_dependency),
    db: Session = Depends(get_db),
) -> DeviceCommandResponse:
    dispatcher = find_user(db, payload.dispatcher_id)
    if dispatcher is None:
        raise HTTPException(status_code=404, detail="Dispatcher not found")
    if dispatcher.role != "dispatcher":
        raise HTTPException(status_code=403, detail="Dispatcher role required")
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=409, detail="Device is inactive") from exc

    if payload.action == "OPEN_LID":
        unresolved_fire = db.scalar(
            select(Alert.id)
            .where(
                Alert.device_id == device_id,
                Alert.alert_type == "FIRE_RISK",
                Alert.is_resolved.is_(False),
            )
            .limit(1)
        )
        if (
            unresolved_fire is not None
            or device.fire_streak > 0
        ):
            raise HTTPException(
                status_code=409,
                detail="OPEN_LID is blocked while fire risk is active",
            )

    public_idempotency_key = payload.idempotency_key or uuid4().hex
    idempotency_key = f"dispatcher:{public_idempotency_key}"
    existing = db.scalar(
        select(DeviceCommand).where(
            DeviceCommand.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if existing.device_id != device_id or existing.action != payload.action:
            raise HTTPException(status_code=409, detail="Idempotency key conflict")
        return _response(existing, existing.status in {"SENT", "ACKED"})

    try:
        command = DeviceCommand(
            device_id=device_id,
            action=payload.action,
            requested_by_id=dispatcher.id,
            idempotency_key=idempotency_key,
            payload={},
        )
        db.add(command)
        db.flush()
        command.payload = {
            "action": payload.action,
            "command_id": command.id,
            "idempotency_key": public_idempotency_key,
        }
        device.lid_status = (
            "OPEN_REQUESTED" if payload.action == "OPEN_LID" else "CLOSE_REQUESTED"
        )
        db.commit()
        db.refresh(command)
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(DeviceCommand).where(
                DeviceCommand.idempotency_key == idempotency_key
            )
        )
        if (
            replay is not None
            and replay.device_id == device_id
            and replay.action == payload.action
            and replay.requested_by_id == dispatcher.id
        ):
            return _response(replay, replay.status in {"SENT", "ACKED"})
        raise HTTPException(status_code=409, detail="Idempotency key conflict") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not persist dispatcher command device=%s", device_id)
        raise HTTPException(status_code=500, detail="Command could not be persisted") from exc

    sent = await send_device_command(device_id, dict(command.payload))
    try:
        persisted = record_delivery(db, command.id, sent)
        if persisted is not None:
            command = persisted
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Could not persist command delivery device=%s", device_id)

    return _response(command, sent)


@router.get("/commands", response_model=list[DeviceCommandResponse])
def list_device_commands(
    device_id: str | None = None,
    command_status: Annotated[
        str | None, Query(alias="status", pattern="^(PENDING|SENT|ACKED|FAILED)$")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    db: Session = Depends(get_db),
) -> list[DeviceCommandResponse]:
    statement = select(DeviceCommand)
    if device_id is not None:
        statement = statement.where(DeviceCommand.device_id == device_id)
    if command_status is not None:
        statement = statement.where(DeviceCommand.status == command_status)
    commands = list(
        db.scalars(statement.order_by(DeviceCommand.id.desc()).limit(limit)).all()
    )
    return [_response(command, command.status in {"SENT", "ACKED"}) for command in commands]
