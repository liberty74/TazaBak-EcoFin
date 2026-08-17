"""Pydantic v2 request and response contracts."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DEVICE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$"
UserRole = Literal["user", "volunteer", "dispatcher"]


class TelemetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(pattern=DEVICE_ID_PATTERN)
    distance: float = Field(ge=0, le=400, allow_inf_nan=False)
    temp_in: float = Field(ge=-60, le=250, allow_inf_nan=False)
    temp_out: float = Field(ge=-60, le=100, allow_inf_nan=False)
    measured_at: datetime | None = None

    @field_validator("measured_at")
    @classmethod
    def normalize_measured_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class TelemetryResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    telemetry_id: int
    device_id: str
    fill_raw_percent: float
    fill_percent: float
    fire_score: float
    fire_streak: int
    fire_risk: bool
    action_triggered: Literal["CLOSE_LID"] | None = None
    command_sent: bool = False
    received_at: datetime


class VisionResponse(BaseModel):
    status: Literal["processed"] = "processed"
    frame_id: int
    device_id: str
    detected: bool
    object_label: Literal["illegal_dump"] | None = None
    confidence: float | None = None
    alert_id: int | None = None
    image_url: str


class DetectedObjectResponse(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    bounding_box: list[float] = Field(min_length=4, max_length=4)


class BioResponse(BaseModel):
    analysis_id: int
    status: Literal["approve", "reject", "invalid"]
    qr_code: str
    points_awarded: int
    current_balance: int
    detected_objects: list[DetectedObjectResponse]
    user_id: int
    image_url: str | None = None
    command_sent: bool = False
    action_triggered: Literal["OPEN_LID"] | None = None
    reason: Literal["mold_detected", "not_bread", "empty_frame"] | None = None


class DispatchAlert(BaseModel):
    id: int
    device_id: str | None
    type: str
    status: str
    message: str
    evidence_url: str | None
    details: dict[str, Any]
    created_at: datetime


class DispatchSummary(BaseModel):
    generated_at: datetime
    total_unresolved: int
    counts_by_type: dict[str, int]
    counts_by_status: dict[str, int]
    tasks: list[DispatchAlert]


class DispatchBriefing(BaseModel):
    generated_at: datetime
    total_tasks: int
    text: str


class ResolveAlertResponse(BaseModel):
    id: int
    status: Literal["resolved"] = "resolved"
    resolved_at: datetime


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    points: int
    status_tier: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=64, pattern=r"^[\w.-]+$")
    password: str = Field(min_length=6, max_length=128)
    role: Literal["user", "volunteer"] = "user"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class PointTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    balance_after: int
    transaction_type: str
    description: str
    reference_id: str | None
    created_at: datetime


class EcoNFTResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    token_id: str
    svg_content: str
    title: str
    creation_date: datetime


class UserDashboardResponse(BaseModel):
    profile: UserProfile
    transactions: list[PointTransactionResponse]
    nfts: list[EcoNFTResponse]


class ContainerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    is_active: bool
    last_fill_level: float
    fill_percent: float


class VolunteerTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    reward_points: int
    date: date
    time: time
    description: str
    status: Literal["open", "completed"]


class VolunteerRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    user_id: str = Field(min_length=1, max_length=64)


class VolunteerRegisterResponse(BaseModel):
    status: Literal["registered"] = "registered"
    user_task_id: int
    registration_id: int
    task_id: int
    user_id: int
    reward_points_pending: int
    points_balance: int


class VolunteerCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    user_id: str = Field(min_length=1, max_length=64)
    dispatcher_id: str = Field(min_length=1, max_length=64)


class VolunteerCompleteResponse(BaseModel):
    status: Literal["completed"] = "completed"
    user_task_id: int
    task_id: int
    user_id: int
    points_awarded: int
    current_balance: int
    completed_at: datetime


class ShopItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    price_points: int
    image_url: str
    is_active: bool


class ShopBuyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    user_id: str = Field(min_length=1, max_length=64)
    item_id: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=64)


class ShopBuyResponse(BaseModel):
    status: Literal["purchased"] = "purchased"
    purchase_id: int
    user_id: int
    item_id: int
    item_title: str
    spent_points: int
    points_balance: int


class MintNFTRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, coerce_numbers_to_str=True
    )

    user_id: str = Field(min_length=1, max_length=64)
    title: str = Field(default="Eco Leaf", min_length=1, max_length=96)
    idempotency_key: str = Field(min_length=8, max_length=64)


class MintNFTResponse(BaseModel):
    status: Literal["minted"] = "minted"
    price_points: int
    current_balance: int
    nft: EcoNFTResponse


class DispatcherCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    dispatcher_id: str = Field(min_length=1, max_length=64)
    action: Literal["OPEN_LID", "CLOSE_LID"]
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=64)


class DeviceCommandResponse(BaseModel):
    id: int
    device_id: str
    action: Literal["OPEN_LID", "CLOSE_LID"]
    status: Literal["PENDING", "SENT", "ACKED", "FAILED"]
    command_sent: bool
    idempotency_key: str
    created_at: datetime


class DeviceTelemetryStatus(BaseModel):
    device_id: str
    lid_status: str
    last_seen_at: datetime
    temperature_in_c: float | None = None
    temperature_out_c: float | None = None
    temperature_delta_c: float | None = None
    measured_at: datetime | None = None
    camera_stream_url: str | None = None


class CameraStreamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stream_url: str = Field(min_length=10, max_length=512)

    @field_validator("stream_url")
    @classmethod
    def validate_stream_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("stream_url must be a valid http(s) URL")
        if parsed.username or parsed.password:
            raise ValueError("stream_url must not include credentials")
        return value


class CameraAnalysisResponse(BaseModel):
    status: Literal["processed"] = "processed"
    frame_id: int
    device_id: str
    detected: bool
    confidence: float | None = None
    detected_objects: list[DetectedObjectResponse]
    image_url: str
    alert_id: int | None = None
    created_at: datetime


class ForumMessageCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, coerce_numbers_to_str=True
    )

    username: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=1000)


class ForumMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    text: str
    timestamp: datetime


class AIChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, coerce_numbers_to_str=True
    )

    message: str = Field(min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)


class AIChatResponse(BaseModel):
    response: str
    provider: Literal["google-gemini", "offline-fallback"]
    model: str | None = None
