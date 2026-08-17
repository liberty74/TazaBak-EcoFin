"""EMA and differential fire-risk processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Alert,
    BinContainer,
    Device,
    DeviceCommand,
    Telemetry,
    utcnow,
)
from app.schemas import TelemetryIn
from app.services.device_activity import ensure_municipal_device_is_active


@dataclass(frozen=True, slots=True)
class TelemetryResult:
    telemetry: Telemetry
    alert_id: int | None
    command_id: int | None
    should_close_lid: bool


class DeviceKindConflictError(RuntimeError):
    """Raised when one physical ID is reused for incompatible device roles."""


def get_or_create_device(db: Session, device_id: str, kind: str) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        device = Device(id=device_id, kind=kind)
        db.add(device)
        db.flush()
    elif device.kind != kind:
        if device.kind == "unknown":
            device.kind = kind
        else:
            raise DeviceKindConflictError(
                f"Device {device_id!r} is registered as {device.kind}, not {kind}"
            )
    return device


def _raw_fill_percent(distance_cm: float) -> float:
    denominator = settings.h_empty_cm - settings.h_full_cm
    if denominator <= 0:
        raise RuntimeError("H_EMPTY_CM must be greater than H_FULL_CM")
    raw_fill = (
        (settings.h_empty_cm - distance_cm) / denominator
    ) * 100.0
    return min(100.0, max(0.0, raw_fill))


def process_telemetry(db: Session, payload: TelemetryIn) -> TelemetryResult:
    """Persist one measurement and derive state from the previous DB row."""

    received_at = utcnow()
    ensure_municipal_device_is_active(db, payload.device_id)
    device = get_or_create_device(db, payload.device_id, "municipal")
    previous = db.scalar(
        select(Telemetry)
        .where(Telemetry.device_id == payload.device_id)
        .order_by(Telemetry.received_at.desc(), Telemetry.id.desc())
        .limit(1)
    )

    fill_raw = _raw_fill_percent(payload.distance)
    # The physical end stops are definitive: at 25 cm the bin is empty, and
    # at 7 cm it is full. EMA still smooths readings between those points.
    if fill_raw in {0.0, 100.0}:
        fill_ema = fill_raw
    else:
        fill_ema = (
            fill_raw
            if previous is None
            else settings.ema_alpha * fill_raw
            + (1.0 - settings.ema_alpha) * previous.fill_ema_percent
        )

    temperature_delta = payload.temp_in - payload.temp_out
    sampling_interval: float | None = None
    delta_rate = 0.0
    if previous is not None:
        actual_interval = (received_at - previous.received_at).total_seconds()
        sampling_interval = max(actual_interval, 0.0)
        safe_interval = max(actual_interval, settings.min_rate_interval_seconds)
        delta_rate = (
            temperature_delta - previous.temperature_delta_c
        ) / safe_interval

    fire_score = (
        settings.fire_weight_delta * temperature_delta
        + settings.fire_weight_rate * delta_rate
    )
    # The prototype has one DS18B20 inside the bin. Fire protection is
    # deliberately based on its absolute value, not on a calculated delta.
    # A reading of exactly 50 C is normal; any value above 50 C is a fire risk.
    is_over_temperature = (
        payload.temp_in > settings.fire_temperature_threshold_c
    )
    was_over_temperature = (
        previous is not None
        and previous.temp_in_c > settings.fire_temperature_threshold_c
    )
    fire_streak = (
        (previous.fire_streak + 1 if was_over_temperature else 1)
        if is_over_temperature
        else 0
    )
    # One alert and close command are created at the start of each hot episode.
    is_new_fire_event = is_over_temperature and not was_over_temperature
    existing_fire_close_id = None
    if is_over_temperature and not is_new_fire_event:
        existing_fire_close_id = db.scalar(
            select(DeviceCommand.id)
            .where(
                DeviceCommand.device_id == payload.device_id,
                DeviceCommand.action == "CLOSE_LID",
                DeviceCommand.status.in_(("PENDING", "SENT")),
            )
            .order_by(DeviceCommand.id.desc())
            .limit(1)
        )
    should_close_lid = is_new_fire_event or existing_fire_close_id is not None

    telemetry = Telemetry(
        device_id=payload.device_id,
        distance_cm=payload.distance,
        temp_in_c=payload.temp_in,
        temp_out_c=payload.temp_out,
        temperature_delta_c=temperature_delta,
        delta_rate_c_per_sec=delta_rate,
        sampling_interval_seconds=sampling_interval,
        fill_raw_percent=fill_raw,
        fill_ema_percent=fill_ema,
        fire_score=fire_score,
        fire_streak=fire_streak,
        measured_at=payload.measured_at or received_at,
        received_at=received_at,
    )
    db.add(telemetry)

    alert: Alert | None = None
    command: DeviceCommand | None = None
    if is_new_fire_event:
        alert = Alert(
            device_id=payload.device_id,
            alert_type="FIRE_RISK",
            status="CRITICAL",
            message=(
                "DS18B20 temperature exceeded the municipal fire threshold"
            ),
            details={
                "temperature_in_c": round(payload.temp_in, 4),
                "fire_temperature_threshold_c": settings.fire_temperature_threshold_c,
                "fire_score": round(fire_score, 4),
                "temperature_delta_c": round(temperature_delta, 4),
                "delta_rate_c_per_sec": round(delta_rate, 4),
            },
        )
        db.add(alert)
        db.flush()
        db.execute(
            update(DeviceCommand)
            .where(
                DeviceCommand.device_id == payload.device_id,
                DeviceCommand.action == "OPEN_LID",
                DeviceCommand.status.in_(("PENDING", "SENT")),
            )
            .values(status="FAILED", last_error="superseded_by_fire_risk")
            .execution_options(synchronize_session=False)
        )
        command = DeviceCommand(
            device_id=payload.device_id,
            action="CLOSE_LID",
            requested_by_id=None,
            idempotency_key=f"fire-alert:{alert.id}",
            payload={},
        )
        db.add(command)
        db.flush()
        command.payload = {
            "action": "CLOSE_LID",
            "command_id": command.id,
            "reason": "FIRE_RISK",
            "alert_id": alert.id,
        }
        device.lid_status = "CLOSE_REQUESTED"

    if should_close_lid and command is None:
        command = db.scalar(
            select(DeviceCommand)
            .where(
                DeviceCommand.device_id == payload.device_id,
                DeviceCommand.action == "CLOSE_LID",
                DeviceCommand.status.in_(("PENDING", "SENT")),
            )
            .order_by(DeviceCommand.id.desc())
            .limit(1)
        )

    device.fire_streak = fire_streak
    device.last_seen_at = received_at
    container = db.scalar(
        select(BinContainer).where(BinContainer.device_id == payload.device_id)
    )
    if container is not None:
        container.last_fill_level = fill_ema
    db.flush()
    alert_id = alert.id if alert is not None else None
    db.commit()

    return TelemetryResult(
        telemetry=telemetry,
        alert_id=alert_id,
        command_id=command.id if command is not None else None,
        should_close_lid=should_close_lid,
    )
