"""Guards for municipal containers taken out of service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BinContainer


class DeviceInactiveError(RuntimeError):
    """Raised when an inactive container tries to send or receive live data."""


def ensure_municipal_device_is_active(db: Session, device_id: str) -> None:
    """Reject a known municipal container that a dispatcher deactivated.

    IDs without a container record are allowed: this preserves the API's
    ability to provision a new hardware unit on its first telemetry packet.
    """

    if device_id in settings.retired_municipal_device_ids:
        raise DeviceInactiveError(f"Device {device_id!r} is retired")

    is_active = db.scalar(
        select(BinContainer.is_active).where(BinContainer.device_id == device_id)
    )
    if is_active is not None and not is_active:
        raise DeviceInactiveError(f"Device {device_id!r} is inactive")
