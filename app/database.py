"""SQLAlchemy engine, base class and request-scoped sessions."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from app.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection: object, _: object) -> None:
        """Enable integrity and improve concurrent read/write behavior."""

        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_compatibility_migrations() -> None:
    """Apply additive SQLite changes that ``create_all`` cannot perform.

    The project uses a local SQLite file during the hackathon. Existing files
    predate account passwords, so this migration adds the nullable column once
    without deleting demo data.
    """

    if not _is_sqlite:
        return

    with engine.begin() as connection:
        columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(users)")).mappings()
        }
        if "password_hash" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)"))
            logger.info("Applied SQLite migration: users.password_hash")

        device_columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(devices)")).mappings()
        }
        if "camera_stream_url" not in device_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN camera_stream_url VARCHAR(512)"))
            logger.info("Applied SQLite migration: devices.camera_stream_url")

        vision_columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(vision_frames)")).mappings()
        }
        if vision_columns and "detections" not in vision_columns:
            connection.execute(
                text("ALTER TABLE vision_frames ADD COLUMN detections JSON NOT NULL DEFAULT '[]'")
            )
            logger.info("Applied SQLite migration: vision_frames.detections")
