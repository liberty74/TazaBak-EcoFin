from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.main as app_main
import app.services.commands as commands_service
import app.services.files as files_service
import app.services.gemini_bot as gemini_service
import app.services.websocket as websocket_service
from app.config import settings
from app.database import Base, get_db
from app.services.seed import seed_initial_data


@pytest.fixture()
def api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker[Session], Path]]:
    """Run the whole API against one isolated, durable SQLite database.

    A file database is intentional: the command delivery service creates its
    own sessions while a WebSocket is active, so an in-memory connection would
    not exercise the real durable-delivery path.
    """

    database_path = tmp_path / "tazabak-test.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )

    @event.listens_for(test_engine, "connect")
    def configure_sqlite(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )
    seed_initial_data(test_session_factory)

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    test_settings = replace(
        settings,
        static_dir=static_dir,
        seed_demo_data=False,
        camera_analysis_enabled=False,
        max_upload_bytes=1024,
        max_image_pixels=100,
    )

    # create_app/lifespan and streamed uploads must use only temporary paths and
    # the test engine. Durable command delivery intentionally bypasses get_db,
    # hence its module-level SessionLocal also needs replacing.
    monkeypatch.setattr(app_main, "settings", test_settings)
    monkeypatch.setattr(app_main, "engine", test_engine)
    monkeypatch.setattr(files_service, "settings", test_settings)
    monkeypatch.setattr(commands_service, "SessionLocal", test_session_factory)
    # Never spend Gemini quota in API tests, even when the shell has a key.
    monkeypatch.setattr(gemini_service.gemini_bot, "_api_key", None)
    monkeypatch.setattr(gemini_service.gemini_bot, "_model", None)

    application = app_main.create_app()

    def override_get_db() -> Iterator[Session]:
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = override_get_db
    websocket_service.connected_devices.clear()
    websocket_service._send_locks.clear()  # type: ignore[attr-defined]

    try:
        with TestClient(application) as client:
            yield client, test_session_factory, static_dir
    finally:
        application.dependency_overrides.clear()
        websocket_service.connected_devices.clear()
        websocket_service._send_locks.clear()  # type: ignore[attr-defined]
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()
