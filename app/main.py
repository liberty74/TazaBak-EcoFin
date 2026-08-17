"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app import models as _models  # noqa: F401 - register SQLAlchemy metadata
from app.api import (
    ai_chat,
    auth,
    bio,
    camera,
    community,
    dispatch,
    dispatcher,
    sensors,
    shop,
    users,
    vision,
    volunteer,
    websocket,
)
from app.config import settings
from app.database import Base, apply_compatibility_migrations, engine, get_db
from app.logging_config import configure_logging
from app.middleware import RequestBodyLimitMiddleware, RequestBodyTooLarge
from app.services.seed import seed_initial_data
from app.services.camera_vision import camera_analysis_loop


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.static_dir.mkdir(parents=True, exist_ok=True)
    (settings.static_dir / "vision").mkdir(parents=True, exist_ok=True)
    (settings.static_dir / "bio").mkdir(parents=True, exist_ok=True)
    (settings.static_dir / "shop").mkdir(parents=True, exist_ok=True)

    # Required zero-migration bootstrap for the hackathon SQLite deployment.
    Base.metadata.create_all(bind=engine)
    apply_compatibility_migrations()
    if settings.seed_demo_data:
        seed_initial_data()
    logger.info(
        "TazaBAK API started database=%s static_dir=%s",
        settings.database_url,
        settings.static_dir,
    )
    logger.info(
        "Gemini assistant mode=%s model=%s",
        "enabled" if settings.gemini_api_key else "offline-fallback",
        settings.gemini_model,
    )
    camera_task: asyncio.Task[None] | None = None
    if settings.camera_analysis_enabled:
        camera_session_factory = sessionmaker(
            bind=engine,
            class_=Session,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        camera_task = asyncio.create_task(
            camera_analysis_loop(camera_session_factory),
            name="esp32-camera-yolo-worker",
        )
    try:
        yield
    finally:
        if camera_task is not None:
            camera_task.cancel()
            with suppress(asyncio.CancelledError):
                await camera_task
        logger.info("TazaBAK API stopped")


def create_app() -> FastAPI:
    # StaticFiles validates the directory while the application is imported.
    settings.static_dir.mkdir(parents=True, exist_ok=True)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Smart City API for the Миска добра web application, bread-sharing "
            "boxes, municipal telemetry, incident vision and volunteer workflows."
        ),
        lifespan=lifespan,
    )

    application.include_router(sensors.router)
    application.include_router(vision.router)
    application.include_router(bio.router)
    application.include_router(dispatch.router)
    application.include_router(dispatcher.router)
    application.include_router(users.router)
    application.include_router(volunteer.router)
    application.include_router(shop.router)
    application.include_router(community.router)
    application.include_router(ai_chat.router)
    application.include_router(auth.router)
    application.include_router(camera.router)
    application.include_router(websocket.router)
    application.mount(
        "/static", StaticFiles(directory=settings.static_dir), name="static"
    )

    @application.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        if request.url.path in {"/api/vision/frame", "/api/bio/analyze"}:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    body_size = int(content_length)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header"},
                    )
                # Leave room for normal multipart headers and small text fields.
                if body_size > settings.max_upload_bytes + 256 * 1024:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large"},
                    )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request failure method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        if isinstance(exc, RequestBodyTooLarge):
            raise exc
        logger.exception(
            "Unhandled application exception method=%s path=%s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @application.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    @application.get("/health", tags=["system"])
    def health(db: Session = Depends(get_db)) -> dict[str, str]:
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.exception("Database health check failed")
            raise RuntimeError("Database is unavailable") from exc
        return {"status": "ok", "database": "reachable"}

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        # Dispatcher camera configuration uses PUT.  It must be explicitly
        # allowed so browsers can complete the CORS preflight request.
        allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=settings.max_upload_bytes + 256 * 1024,
        paths=("/api/vision/frame", "/api/bio/analyze"),
    )

    return application


app = create_app()
