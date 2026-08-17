"""Low-level ASGI guards applied before multipart parsing."""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Count streamed HTTP body bytes, including chunked multipart requests."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        paths: tuple[str, ...],
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large"},
                headers={"Connection": "close"},
            )
            await response(scope, receive, send)
