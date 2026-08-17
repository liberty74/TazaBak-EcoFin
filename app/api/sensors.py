"""Municipal sensor ingestion endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DeviceCommand
from app.schemas import TelemetryIn, TelemetryResponse
from app.services.commands import record_delivery
from app.services.device_locks import serialize_device
from app.services.device_activity import DeviceInactiveError
from app.services.telemetry import DeviceKindConflictError, process_telemetry
from app.services.websocket import send_device_command


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post(
    "/ingest",
    response_model=TelemetryResponse,
    status_code=status.HTTP_200_OK,
)
async def ingest_telemetry(
    payload: TelemetryIn,
    db: Session = Depends(get_db),
) -> TelemetryResponse:
    """Store telemetry, update fill EMA and apply the DS18B20 fire interlock."""

    async with serialize_device(payload.device_id):
        try:
            result = process_telemetry(db, payload)
        except DeviceInactiveError as exc:
            db.rollback()
            logger.info("Ignored telemetry from inactive device=%s", payload.device_id)
            raise HTTPException(status_code=409, detail="Device is inactive") from exc
        except DeviceKindConflictError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (SQLAlchemyError, RuntimeError) as exc:
            db.rollback()
            logger.exception(
                "Telemetry transaction failed for device=%s", payload.device_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Telemetry could not be persisted",
            ) from exc

        command_sent = False
        if result.should_close_lid and result.command_id is not None:
            command = db.get(DeviceCommand, result.command_id)
            command_payload = (
                dict(command.payload)
                if command is not None
                else {"action": "CLOSE_LID", "command_id": result.command_id}
            )
            command_sent = await send_device_command(
                payload.device_id, command_payload
            )
            try:
                record_delivery(db, result.command_id, command_sent)
            except SQLAlchemyError:
                db.rollback()
                logger.exception(
                    "Could not persist close delivery device=%s command=%s",
                    payload.device_id,
                    result.command_id,
                )
            logger.critical(
                "Fire trigger device=%s alert_id=%s command_sent=%s",
                payload.device_id,
                result.alert_id,
                command_sent,
            )

        telemetry = result.telemetry
        return TelemetryResponse(
            telemetry_id=telemetry.id,
            device_id=telemetry.device_id,
            fill_raw_percent=round(telemetry.fill_raw_percent, 4),
            fill_percent=round(telemetry.fill_ema_percent, 4),
            fire_score=round(telemetry.fire_score, 4),
            fire_streak=telemetry.fire_streak,
            fire_risk=(
                telemetry.temp_in_c > settings.fire_temperature_threshold_c
            ),
            action_triggered="CLOSE_LID" if result.should_close_lid else None,
            command_sent=command_sent,
            received_at=telemetry.received_at,
        )
