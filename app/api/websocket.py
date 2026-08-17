"""Device command WebSocket endpoint."""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool

from app.schemas import DEVICE_ID_PATTERN
from app.services.commands import acknowledge_command, deliver_pending_commands
from app.services.device_locks import serialize_device
from app.services.websocket import (
    register_device,
    send_device_reply,
    unregister_device,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["devices"])


@router.websocket("/ws/device/{device_id}")
async def device_websocket(websocket: WebSocket, device_id: str) -> None:
    await websocket.accept()
    if re.fullmatch(DEVICE_ID_PATTERN, device_id) is None:
        await websocket.close(code=1008, reason="Invalid device_id")
        return
    await register_device(device_id, websocket)
    logger.info("WebSocket connected device=%s", device_id)
    delivered = await deliver_pending_commands(device_id)
    if delivered:
        logger.info(
            "Delivered pending commands device=%s count=%s", device_id, delivered
        )
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await send_device_reply(
                    device_id,
                    websocket,
                    {"action": "ERROR", "reason": "invalid_json"},
                )
                continue

            if not isinstance(message, dict):
                await send_device_reply(
                    device_id,
                    websocket,
                    {"action": "ERROR", "reason": "json_object_required"},
                )
                continue

            action = message.get("action")
            if action == "PING":
                response = {"action": "PONG"}
            elif action in {"COMMAND_ACK", "ACK"} and isinstance(
                message.get("command_id"), int
            ):
                async with serialize_device(device_id):
                    acknowledged = await run_in_threadpool(
                        acknowledge_command, device_id, message["command_id"]
                    )
                response = {
                    "action": "ACK_CONFIRMED" if acknowledged else "ERROR",
                    "command_id": message["command_id"],
                    "reason": None if acknowledged else "command_not_found",
                }
            else:
                response = {"action": "ACK", "received": action}
            await send_device_reply(device_id, websocket, response)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected device=%s", device_id)
    except RuntimeError:
        logger.exception("WebSocket runtime failure device=%s", device_id)
    finally:
        unregister_device(device_id, websocket)
