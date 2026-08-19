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
        # A fresh checkout has no database file yet. PRAGMA on a missing table
        # returns nothing, so an unguarded ALTER would fail on first start.
        existing_tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }
        if "users" not in existing_tables:
            logger.debug("Skipping SQLite migrations: schema not created yet")
            return

        columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(users)")).mappings()
        }
        if "password_hash" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)"))
            logger.info("Applied SQLite migration: users.password_hash")
        if "school_class" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN school_class VARCHAR(32)"))
            logger.info("Applied SQLite migration: users.school_class")

        profile_columns = {
            row["name"]
            for row in connection.execute(
                text("PRAGMA table_info(cost_profiles)")
            ).mappings()
        }
        if profile_columns and "depot_latitude" not in profile_columns:
            # Kokshetau depot, refined on site. A closed tour needs a start.
            connection.execute(
                text(
                    "ALTER TABLE cost_profiles "
                    "ADD COLUMN depot_latitude FLOAT NOT NULL DEFAULT 53.2650"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE cost_profiles "
                    "ADD COLUMN depot_longitude FLOAT NOT NULL DEFAULT 69.4300"
                )
            )
            logger.info("Applied SQLite migration: cost_profiles depot coordinates")

        if profile_columns and "hardware_cost_kzt" not in profile_columns:
            # Параметры выручки: себестоимость железа, тариф для бизнеса,
            # цена углеродной единицы и ставка спонсора.
            for column, default in (
                ("hardware_cost_kzt", "21500.0"),
                ("business_subscription_kzt_per_month", "9000.0"),
                ("carbon_price_kzt_per_ton", "2500.0"),
                ("sponsor_kzt_per_active_resident", "150.0"),
            ):
                connection.execute(
                    text(
                        "ALTER TABLE cost_profiles "
                        f"ADD COLUMN {column} FLOAT NOT NULL DEFAULT {default}"
                    )
                )
            logger.info("Applied SQLite migration: cost_profiles revenue parameters")

        device_columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(devices)")).mappings()
        }
        if device_columns and "camera_stream_url" not in device_columns:
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

        bio_columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(bio_analyses)")).mappings()
        }
        if bio_columns and "classification" not in bio_columns:
            # Analyses recorded before CLIP keep an empty object: they were
            # decided by the old COCO rule and must not look like CLIP results.
            connection.execute(
                text(
                    "ALTER TABLE bio_analyses "
                    "ADD COLUMN classification JSON NOT NULL DEFAULT '{}'"
                )
            )
            logger.info("Applied SQLite migration: bio_analyses.classification")
