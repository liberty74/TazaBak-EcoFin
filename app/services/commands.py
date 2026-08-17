"""Durable delivery and acknowledgement helpers for device commands."""

from __future__ import annotations

import logging

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, Device, DeviceCommand, utcnow
from app.services.device_locks import serialize_device
from app.services.websocket import send_device_command


logger = logging.getLogger(__name__)


def record_delivery(
    db: Session, command_id: int, delivered: bool
) -> DeviceCommand | None:
    """Persist a delivery attempt without overwriting a concurrent ACK."""

    values: dict[str, object] = {
        "attempts": DeviceCommand.attempts + 1,
        "last_error": None if delivered else "device_offline_or_delivery_failed",
    }
    if delivered:
        values.update(status="SENT", sent_at=utcnow())
    db.execute(
        update(DeviceCommand)
        .where(
            DeviceCommand.id == command_id,
            DeviceCommand.status.in_(("PENDING", "SENT")),
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
    return db.get(DeviceCommand, command_id)


async def deliver_pending_commands(device_id: str) -> int:
    """Redeliver every unacknowledged, unexpired command on reconnect."""

    async with serialize_device(device_id):
        return await _deliver_pending_commands_locked(device_id)


async def _deliver_pending_commands_locked(device_id: str) -> int:

    delivered = 0
    now = utcnow()
    with SessionLocal() as db:
        device = db.get(Device, device_id)
        unresolved_fire = db.scalar(
            select(Alert.id)
            .where(
                Alert.device_id == device_id,
                Alert.alert_type == "FIRE_RISK",
                Alert.is_resolved.is_(False),
            )
            .limit(1)
        )
        if unresolved_fire is not None or (
            device is not None
            and device.fire_streak > 0
        ):
            db.execute(
                update(DeviceCommand)
                .where(
                    DeviceCommand.device_id == device_id,
                    DeviceCommand.action == "OPEN_LID",
                    DeviceCommand.status.in_(("PENDING", "SENT")),
                )
                .values(status="FAILED", last_error="blocked_by_fire_interlock")
                .execution_options(synchronize_session=False)
            )
        db.execute(
            update(DeviceCommand)
            .where(
                DeviceCommand.device_id == device_id,
                DeviceCommand.status.in_(("PENDING", "SENT")),
                DeviceCommand.expires_at.is_not(None),
                DeviceCommand.expires_at <= now,
            )
            .values(status="FAILED", last_error="command_expired")
            .execution_options(synchronize_session=False)
        )
        db.commit()
        commands = list(
            db.scalars(
                select(DeviceCommand)
                .where(
                    DeviceCommand.device_id == device_id,
                    DeviceCommand.status.in_(("PENDING", "SENT")),
                    or_(
                        DeviceCommand.expires_at.is_(None),
                        DeviceCommand.expires_at > now,
                    ),
                )
                .order_by(DeviceCommand.id.asc())
                .limit(100)
            ).all()
        )
        for command in commands:
            payload = dict(command.payload)
            payload.setdefault("action", command.action)
            payload.setdefault("command_id", command.id)
            sent = await send_device_command(device_id, payload)
            try:
                # Commit before the next network await so a slow socket cannot
                # retain SQLite's process-wide writer lock.
                record_delivery(db, command.id, sent)
            except SQLAlchemyError:
                db.rollback()
                logger.exception(
                    "Could not persist command delivery device=%s command=%s",
                    device_id,
                    command.id,
                )
                break
            if sent:
                delivered += 1
            if not sent:
                break
    return delivered


def acknowledge_command(device_id: str, command_id: int) -> bool:
    with SessionLocal() as db:
        command = db.get(DeviceCommand, command_id)
        if command is None or command.device_id != device_id:
            return False
        if command.status == "ACKED":
            return True
        if command.status not in {"PENDING", "SENT"}:
            return False

        device = db.get(Device, device_id)
        if command.action == "OPEN_LID":
            unresolved_fire = db.scalar(
                select(Alert.id)
                .where(
                    Alert.device_id == device_id,
                    Alert.alert_type == "FIRE_RISK",
                    Alert.is_resolved.is_(False),
                )
                .limit(1)
            )
            if unresolved_fire is not None or (
                device is not None
                and device.fire_streak > 0
            ):
                command.status = "FAILED"
                command.last_error = "ack_rejected_by_fire_interlock"
                if device is not None:
                    device.lid_status = "CLOSE_REQUESTED"
                db.commit()
                return False

        newer_command_id = db.scalar(
            select(DeviceCommand.id)
            .where(
                DeviceCommand.device_id == device_id,
                DeviceCommand.id > command.id,
                DeviceCommand.status.in_(("PENDING", "SENT", "ACKED")),
            )
            .order_by(DeviceCommand.id.desc())
            .limit(1)
        )
        command.status = "ACKED"
        command.acknowledged_at = utcnow()
        command.last_error = None
        db.execute(
            update(DeviceCommand)
            .where(
                DeviceCommand.device_id == device_id,
                DeviceCommand.id < command.id,
                DeviceCommand.status.in_(("PENDING", "SENT")),
            )
            .values(
                status="FAILED",
                last_error=f"superseded_by_ack:{command.id}",
            )
            .execution_options(synchronize_session=False)
        )
        if device is not None and newer_command_id is None:
            device.lid_status = (
                "OPEN" if command.action == "OPEN_LID" else "CLOSED"
            )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception(
                "Could not persist command ACK device=%s command=%s",
                device_id,
                command_id,
            )
            return False
        return True
