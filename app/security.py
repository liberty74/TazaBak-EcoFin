"""Small API-key guard for privileged dispatcher operations."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings


dispatcher_key_header = APIKeyHeader(
    name="X-Dispatcher-Key",
    scheme_name="DispatcherApiKey",
    auto_error=False,
)


def require_dispatcher_key(
    supplied_key: Annotated[str | None, Security(dispatcher_key_header)],
) -> None:
    if supplied_key is None or not secrets.compare_digest(
        supplied_key, settings.dispatcher_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid dispatcher API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
