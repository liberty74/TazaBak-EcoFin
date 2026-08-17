"""MJPEG proxy for ESP32-CAM streams configured by dispatchers."""

from __future__ import annotations

from collections.abc import Iterator

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Device
from app.services.device_activity import (
    DeviceInactiveError,
    ensure_municipal_device_is_active,
)


router = APIRouter(prefix="/api/cameras", tags=["camera stream"])


@router.get("/{device_id}/stream")
def proxy_camera_stream(device_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """Expose a configured local ESP32-CAM MJPEG feed through FastAPI."""

    device = db.get(Device, device_id)
    if device is None or not device.camera_stream_url:
        raise HTTPException(status_code=404, detail="Camera stream is not configured")
    try:
        ensure_municipal_device_is_active(db, device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=404, detail="Camera stream is not configured") from exc
    try:
        upstream = requests.get(device.camera_stream_url, stream=True, timeout=(3, 20))
        upstream.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="ESP32-CAM stream is unavailable") from exc

    content_type = upstream.headers.get("content-type", "multipart/x-mixed-replace")

    def iterator() -> Iterator[bytes]:
        try:
            yield from upstream.iter_content(chunk_size=16 * 1024)
        finally:
            upstream.close()

    return StreamingResponse(
        iterator(),
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )
