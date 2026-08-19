"""Pydantic v2 request and response contracts."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


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


class DetectedObjectResponse(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    bounding_box: list[float] = Field(min_length=4, max_length=4)


class VisionResponse(BaseModel):
    status: Literal["processed"] = "processed"
    frame_id: int
    device_id: str
    detected: bool
    object_label: Literal["illegal_dump"] | None = None
    confidence: float | None = None
    # Every object the detector found, so the alert can be reviewed instead of
    # trusted: the stored frame is unmodified and boxes are drawn from here.
    detected_objects: list[DetectedObjectResponse] = Field(default_factory=list)
    alert_id: int | None = None
    image_url: str


class BreadClassificationResponse(BaseModel):
    """What CLIP compared the photo against, and how strongly it matched.

    The probabilities are part of the answer on purpose: a resident whose
    bread was rejected can see how close the call was.
    """

    decision: Literal["fresh_bread", "moldy_bread", "no_bread"]
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]
    model: str


class BioResponse(BaseModel):
    analysis_id: int
    status: Literal["approve", "reject", "invalid"]
    qr_code: str
    points_awarded: int
    current_balance: int
    detected_objects: list[DetectedObjectResponse]
    classification: BreadClassificationResponse | None = None
    user_id: int
    image_url: str | None = None
    command_sent: bool = False
    action_triggered: Literal["OPEN_LID"] | None = None
    reason: (
        Literal["mold_detected", "not_bread", "empty_frame", "low_confidence"] | None
    ) = None


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


class EcoCostProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_name: str
    city: str
    km_per_stop: float
    minutes_per_stop: float
    fuel_consumption_l_per_100km: float
    fuel_price_kzt_per_liter: float
    crew_cost_kzt_per_hour: float
    baseline_trips_per_week: float
    fill_threshold_percent: float
    co2_kg_per_liter: float
    bread_avg_weight_kg: float
    bread_cost_kzt_per_kg: float
    install_price_kzt: float
    subscription_kzt_per_month: float
    hardware_cost_kzt: float
    business_subscription_kzt_per_month: float
    carbon_price_kzt_per_ton: float
    sponsor_kzt_per_active_resident: float
    updated_at: datetime


class EcoCostProfileUpdate(BaseModel):
    """Every field is optional: a dispatcher tunes one parameter at a time."""

    model_config = ConfigDict(extra="forbid")

    km_per_stop: float | None = Field(default=None, gt=0, le=500)
    minutes_per_stop: float | None = Field(default=None, gt=0, le=600)
    fuel_consumption_l_per_100km: float | None = Field(default=None, gt=0, le=200)
    fuel_price_kzt_per_liter: float | None = Field(default=None, gt=0, le=10_000)
    crew_cost_kzt_per_hour: float | None = Field(default=None, ge=0, le=1_000_000)
    baseline_trips_per_week: float | None = Field(default=None, gt=0, le=21)
    fill_threshold_percent: float | None = Field(default=None, gt=0, le=100)
    co2_kg_per_liter: float | None = Field(default=None, gt=0, le=10)
    bread_avg_weight_kg: float | None = Field(default=None, gt=0, le=10)
    bread_cost_kzt_per_kg: float | None = Field(default=None, ge=0, le=100_000)
    install_price_kzt: float | None = Field(default=None, ge=0, le=100_000_000)
    subscription_kzt_per_month: float | None = Field(default=None, ge=0, le=10_000_000)
    hardware_cost_kzt: float | None = Field(default=None, ge=0, le=100_000_000)
    business_subscription_kzt_per_month: float | None = Field(
        default=None, ge=0, le=10_000_000
    )
    carbon_price_kzt_per_ton: float | None = Field(default=None, ge=0, le=1_000_000)
    sponsor_kzt_per_active_resident: float | None = Field(
        default=None, ge=0, le=1_000_000
    )


class EcoTrips(BaseModel):
    baseline: float
    actual: int
    saved: float
    reduction_percent: float
    average_fill_at_collection_percent: float | None = None


class EcoResources(BaseModel):
    km_saved: float
    liters_saved: float
    co2_kg_saved: float


class EcoMoney(BaseModel):
    fuel_kzt: float
    crew_kzt: float
    total_kzt: float


class EcoBread(BaseModel):
    """Bread kept out of the bin.

    ``rescued_value_kzt`` is the cost of the product that reached a shelter
    instead of a landfill. It is deliberately kept apart from ``EcoMoney``:
    the bakery does not get this money back, so adding it to fuel savings
    would overstate the operator's return.
    """

    kg_from_citizens: float
    kg_from_business: float
    kg_total: float
    rescued_value_kzt: float


class EcoPayback(BaseModel):
    monthly_savings_kzt: float
    monthly_subscription_kzt: float
    net_monthly_kzt: float
    install_total_kzt: float
    payback_months: float | None = None


class EcoWeeklyPoint(BaseModel):
    week_start: date
    trips_saved: float
    kzt_saved: float
    co2_kg_saved: float
    # Последняя корзина периода почти всегда короче семи дней. Без этой
    # пометки график падал бы на ней в пол и читался как обвал экономии,
    # хотя неделя просто ещё не закончилась.
    is_partial: bool = False


class EcoFormulaInputs(BaseModel):
    """Raw inputs behind the report, so any figure can be traced on stage."""

    days: float
    containers: int
    km_per_stop: float
    minutes_per_stop: float
    fuel_consumption_l_per_100km: float
    fuel_price_kzt_per_liter: float
    crew_cost_kzt_per_hour: float
    baseline_trips_per_week: float
    co2_kg_per_liter: float
    km_per_saved_stop: float
    liters_per_saved_stop: float
    kzt_per_saved_stop: float


class SavingsReport(BaseModel):
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    profile_id: int
    org_name: str
    city: str
    containers: int
    trips: EcoTrips
    resources: EcoResources
    money: EcoMoney
    bread: EcoBread
    payback: EcoPayback
    weekly: list[EcoWeeklyPoint]
    formula: EcoFormulaInputs


class RevenueStream(BaseModel):
    """One way the platform earns, with the arithmetic that produced it."""

    key: str
    title: str
    monthly_kzt: float
    # Строка вида «10 баков × 1 000 ₸» — чтобы число можно было проверить
    # на экране, не открывая исходники.
    basis: str
    note: str
    # Маржа на железе разовая, поэтому не попадает в регулярную выручку.
    is_recurring: bool


class RevenueScenario(BaseModel):
    title: str
    containers: int
    streams: list[RevenueStream]
    monthly_recurring_kzt: float
    one_time_kzt: float
    annual_recurring_kzt: float


class RevenueModel(BaseModel):
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    currency: str
    pilot: RevenueScenario
    # Проекция отделена от факта намеренно: выдать её за измерение —
    # самый быстрый способ провалить техзащиту.
    projection: RevenueScenario | None
    assumptions: list[str]


class CollectionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    container_id: int | None
    collected_at: datetime
    fill_ema_before_percent: float
    fill_raw_before_percent: float
    source: Literal["SENSOR", "DISPATCHER", "SEED"]


class CollectionEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(pattern=DEVICE_ID_PATTERN)
    idempotency_key: str = Field(min_length=8, max_length=64)
    collected_at: datetime | None = None

    @field_validator("collected_at")
    @classmethod
    def normalize_collected_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class SavingsSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    period_start: datetime
    period_end: datetime
    containers: int
    trips_baseline: float
    trips_actual: int
    trips_saved: float
    km_saved: float
    liters_saved: float
    kzt_saved: float
    co2_kg_saved: float
    bread_kg_saved: float
    bread_kzt_saved: float
    created_at: datetime


class WriteOffCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    occurred_on: date
    product: str = Field(min_length=1, max_length=64)
    kg_written_off: float = Field(ge=0, le=10_000, allow_inf_nan=False)
    kg_donated: float = Field(default=0.0, ge=0, le=10_000, allow_inf_nan=False)
    cost_kzt_per_kg: float = Field(ge=0, le=100_000, allow_inf_nan=False)

    @field_validator("kg_donated")
    @classmethod
    def donated_within_written(cls, value: float, info: ValidationInfo) -> float:
        written = info.data.get("kg_written_off")
        if written is not None and value > written:
            raise ValueError("kg_donated must not exceed kg_written_off")
        return value


class WriteOffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    occurred_on: date
    product: str
    kg_written_off: float
    kg_donated: float
    cost_kzt_per_kg: float
    updated_at: datetime


class ContainerForecast(BaseModel):
    container_id: int
    device_id: str
    name: str
    latitude: float
    longitude: float
    fill_percent: float
    threshold_percent: float
    samples: int
    status: Literal["due_now", "forecast", "unavailable"]
    rate_percent_per_hour: float | None = None
    r_squared: float | None = None
    eta_hours: float | None = None
    eta_at: datetime | None = None
    reason: Literal["not_enough_measurements", "not_filling"] | None = None


class RouteScenario(BaseModel):
    label: str
    stops: int
    distance_km: float
    liters: float
    kzt: float


class RouteLeg(BaseModel):
    position: int
    from_label: str
    to_label: str
    container_id: int | None = None
    distance_km: float


class RoutePlan(BaseModel):
    generated_at: datetime
    horizon_hours: float
    baseline: RouteScenario
    planned: RouteScenario
    distance_saved_km: float
    liters_saved: float
    kzt_saved: float
    co2_kg_saved: float
    legs: list[RouteLeg]
    skipped: list[str]


class ProductForecast(BaseModel):
    product: str
    expected_kg: float
    average_kg: float
    deviation_percent: float
    samples: int
    basis: Literal["same_weekday", "all_days"]


class WeekdayProfile(BaseModel):
    weekday: int = Field(ge=0, le=6)
    name: str
    average_kg: float
    samples: int


class BusinessForecast(BaseModel):
    profile_id: int
    org_name: str
    target_date: date
    target_weekday: str
    lookback_weeks: int
    products: list[ProductForecast]
    weekday_profile: list[WeekdayProfile]
    history_days: int
    total_written_off_kg: float
    total_donated_kg: float
    donation_rate_percent: float
    # Cost of the product that reached a shelter instead of a landfill. Not
    # money returned to the bakery — the product was already written off.
    rescued_value_kzt: float


class SchoolClassStanding(BaseModel):
    school_class: str
    pupils: int
    points: int
    accepted_items: int
    bread_kg: float
    bread_kzt: float


class EcoRecommendation(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=600)


class EcoRecommendations(BaseModel):
    """Advice for tomorrow, together with the numbers it was allowed to use.

    ``facts`` is not decoration: the recommendations are machine-checked
    against it, and returning it lets anyone repeat that check.
    """

    generated_at: datetime
    provider: Literal["google-gemini", "offline-fallback"]
    model: str | None = None
    facts: dict[str, Any]
    recommendations: list[EcoRecommendation]


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
