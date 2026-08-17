"""SQLAlchemy domain models for the TazaBAK modular monolith."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base


def utcnow() -> datetime:
    """Return naive UTC, stored consistently by SQLite."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), default="municipal", nullable=False)
    fire_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lid_status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    camera_stream_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    telemetry: Mapped[list["Telemetry"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="device")
    container: Mapped["BinContainer | None"] = relationship(back_populates="device")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("points >= 0", name="ck_users_points_nonnegative"),
        CheckConstraint(
            "role IN ('user', 'volunteer', 'dispatcher')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False, index=True)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_tier: Mapped[str] = mapped_column(
        String(64), default="Eco-Starter", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user_tasks: Mapped[list["UserTask"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    purchases: Mapped[list["ShopPurchase"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    point_transactions: Mapped[list["PointTransaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    nfts: Mapped[list["EcoNFT"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    bio_analyses: Mapped[list["BioAnalysis"]] = relationship(back_populates="user")


class BinContainer(Base):
    __tablename__ = "bin_containers"
    __table_args__ = (
        CheckConstraint(
            "last_fill_level >= 0 AND last_fill_level <= 100",
            name="ck_bin_fill_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(256), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fill_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    device: Mapped[Device] = relationship(back_populates="container")


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (
        Index("ix_telemetry_device_received", "device_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    distance_cm: Mapped[float] = mapped_column(Float, nullable=False)
    temp_in_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_out_c: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_delta_c: Mapped[float] = mapped_column(Float, nullable=False)
    delta_rate_c_per_sec: Mapped[float] = mapped_column(Float, nullable=False)
    sampling_interval_seconds: Mapped[float | None] = mapped_column(Float)
    fill_raw_percent: Mapped[float] = mapped_column(Float, nullable=False)
    fill_ema_percent: Mapped[float] = mapped_column(Float, nullable=False)
    fire_score: Mapped[float] = mapped_column(Float, nullable=False)
    fire_streak: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    device: Mapped[Device] = relationship(back_populates="telemetry")

    distance = synonym("distance_cm")
    temp_in = synonym("temp_in_c")
    temp_out = synonym("temp_out_c")
    timestamp = synonym("measured_at")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_open_created", "is_resolved", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_path: Mapped[str | None] = mapped_column(String(512))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    device: Mapped[Device | None] = relationship(back_populates="alerts")

    type = synonym("alert_type")
    image_path = synonym("evidence_path")
    timestamp = synonym("created_at")


class VolunteerTask(Base):
    __tablename__ = "volunteer_tasks"
    __table_args__ = (
        CheckConstraint(
            "reward_points >= 0", name="ck_volunteer_tasks_reward_nonnegative"
        ),
        CheckConstraint(
            "status IN ('open', 'completed')", name="ck_volunteer_tasks_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[time] = mapped_column(Time, default=time(10, 0), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user_tasks: Mapped[list["UserTask"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class UserTask(Base):
    __tablename__ = "user_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", name="uq_user_task"),
        CheckConstraint(
            "status IN ('registered', 'completed')", name="ck_user_tasks_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("volunteer_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="registered", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reward_points_snapshot: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reward_points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="user_tasks")
    task: Mapped[VolunteerTask] = relationship(back_populates="user_tasks")


class ShopItem(Base):
    __tablename__ = "shop_items"
    __table_args__ = (
        CheckConstraint("price_points >= 0", name="ck_shop_items_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price_points: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    purchases: Mapped[list["ShopPurchase"]] = relationship(back_populates="item")


class ShopPurchase(Base):
    __tablename__ = "shop_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("shop_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    price_points: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="purchases")
    item: Mapped[ShopItem] = relationship(back_populates="purchases")


class PointTransaction(Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        CheckConstraint("amount != 0", name="ck_point_transactions_nonzero"),
        CheckConstraint(
            "balance_after >= 0", name="ck_point_transactions_balance_nonnegative"
        ),
        UniqueConstraint(
            "transaction_type", "reference_id", name="uq_point_transaction_reference"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="point_transactions")


class DeviceCommand(Base):
    __tablename__ = "device_commands"
    __table_args__ = (
        CheckConstraint(
            "action IN ('OPEN_LID', 'CLOSE_LID')", name="ck_device_commands_action"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'SENT', 'ACKED', 'FAILED')",
            name="ck_device_commands_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="PENDING", nullable=False, index=True
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(96), unique=True, nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class EcoNFT(Base):
    __tablename__ = "eco_nfts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    mint_idempotency_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    svg_content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    owner: Mapped[User] = relationship(back_populates="nfts")


class ForumMessage(Base):
    __tablename__ = "forum_messages"
    __table_args__ = (Index("ix_forum_timestamp_id", "timestamp", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class VisionFrame(Base):
    __tablename__ = "vision_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    detections: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class BioAnalysis(Base):
    __tablename__ = "bio_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_path: Mapped[str | None] = mapped_column(String(512))
    image_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64))
    qr_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(160), unique=True, nullable=False, index=True
    )
    detected_objects: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(64), default="yolov8n.pt", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User | None] = relationship(back_populates="bio_analyses")


# Temporary import compatibility for code/tests written against v2.
VolunteerRegistration = UserTask
