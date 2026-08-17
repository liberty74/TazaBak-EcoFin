"""Single-process device WebSocket registry."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from app.config import settings


logger = logging.getLogger(__name__)

# Deliberately process-local for the hackathon deployment (one Uvicorn worker).
connected_devices: dict[str, WebSocket] = {}
_send_locks: dict[str, asyncio.Lock] = {}


async def register_device(device_id: str, websocket: WebSocket) -> None:
    previous = connected_devices.get(device_id)
    connected_devices[device_id] = websocket
    _send_locks[device_id] = asyncio.Lock()

    if previous is not None and previous is not websocket:
        logger.warning("Replacing an existing WebSocket for device=%s", device_id)
        try:
            await previous.close(code=1012, reason="Device reconnected")
        except Exception:
            logger.debug("Previous socket for device=%s was already closed", device_id)


def unregister_device(device_id: str, websocket: WebSocket) -> None:
    if connected_devices.get(device_id) is websocket:
        connected_devices.pop(device_id, None)
        _send_locks.pop(device_id, None)


async def send_device_command(device_id: str, payload: dict[str, Any]) -> bool:
    websocket = connected_devices.get(device_id)
    send_lock = _send_locks.get(device_id)
    if websocket is None or send_lock is None:
        logger.warning("No active WebSocket for device=%s", device_id)
        return False

    try:
        async with send_lock:
            if connected_devices.get(device_id) is not websocket:
                return False
            await asyncio.wait_for(
                websocket.send_json(payload),
                timeout=settings.websocket_send_timeout_seconds,
            )
        logger.info("Sent command to device=%s payload=%s", device_id, payload)
        return True
    except Exception:
        logger.exception("Failed to send command to device=%s", device_id)
        unregister_device(device_id, websocket)
        return False


async def send_device_reply(
    device_id: str, websocket: WebSocket, payload: dict[str, Any]
) -> bool:
    send_lock = _send_locks.get(device_id)
    if connected_devices.get(device_id) is not websocket or send_lock is None:
        return False
    try:
        async with send_lock:
            await asyncio.wait_for(
                websocket.send_json(payload),
                timeout=settings.websocket_send_timeout_seconds,
            )
        return True
    except Exception:
        unregister_device(device_id, websocket)
        return False
