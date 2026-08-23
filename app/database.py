"""SQLAlchemy engine, base class and request-scoped sessions."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from app.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")

# pool_pre_ping ловит соединения, разорванные сервером после простоя — на
# PostgreSQL за linger-таймаутом это случается, на файле SQLite проверка
# просто ничего не стоит.
_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.database_url, **_engine_kwargs)
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
    """Apply additive column changes that ``create_all`` cannot perform.

    ``create_all`` builds missing tables but never alters existing ones, so a
    database created by an earlier version keeps its old column set. These
    migrations add the missing columns in place, without dropping demo data.

    The schema is inspected through SQLAlchemy rather than ``PRAGMA``: the same
    code then covers both SQLite and PostgreSQL. Skipping the whole routine on
    PostgreSQL used to be safe only because every PostgreSQL database was
    brand new — the next schema addition would have silently missed it.
    """

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "users" not in existing_tables:
        logger.debug("Skipping compatibility migrations: schema not created yet")
        return

    def columns_of(table: str) -> set[str]:
        if table not in existing_tables:
            return set()
        return {column["name"] for column in inspector.get_columns(table)}

    # Оба диалекта понимают этот минимальный набор типов одинаково; JSON в
    # PostgreSQL становится настоящим json-столбцом, в SQLite — текстом.
    additions: tuple[tuple[str, str, str, str | None], ...] = (
        ("users", "password_hash", "VARCHAR(256)", None),
        ("cost_profiles", "depot_latitude", "FLOAT", "53.2650"),
        ("cost_profiles", "depot_longitude", "FLOAT", "69.4300"),
        ("cost_profiles", "hardware_cost_kzt", "FLOAT", "21500.0"),
        ("cost_profiles", "business_subscription_kzt_per_month", "FLOAT", "9000.0"),
        ("cost_profiles", "carbon_price_kzt_per_ton", "FLOAT", "2500.0"),
        ("cost_profiles", "sponsor_kzt_per_active_resident", "FLOAT", "150.0"),
        ("devices", "camera_stream_url", "VARCHAR(512)", None),
        ("devices", "has_hardware", "BOOLEAN", "FALSE"),
        # Замеры, сделанные до появления флага, действительно приходили с
        # подключённым DS18B20 — иначе прошивка их просто не отправляла.
        ("telemetry", "temp_sensor_ok", "BOOLEAN", "TRUE"),
        ("vision_frames", "detections", "JSON", "'[]'"),
        # Анализы до CLIP остаются с пустым объектом: их решала старая
        # COCO-эвристика, и выдавать их за результат CLIP нельзя.
        ("bio_analyses", "classification", "JSON", "'{}'"),
    )

    with engine.begin() as connection:
        for table, column, column_type, default in additions:
            if column in columns_of(table):
                continue
            if table not in existing_tables:
                continue
            clause = f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
            if default is not None:
                clause += f" NOT NULL DEFAULT {default}"
            connection.execute(text(clause))
            logger.info("Applied migration: %s.%s", table, column)
