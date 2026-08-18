"""EcoFin endpoints: savings, cost parameters, collections and write-offs."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    BinContainer,
    CollectionEvent,
    CostProfile,
    Device,
    SavingsSnapshot,
    WriteOffRecord,
    utcnow,
)
from app.schemas import (
    BusinessForecast,
    CollectionEventCreate,
    CollectionEventResponse,
    ContainerForecast,
    EcoCostProfileResponse,
    EcoCostProfileUpdate,
    EcoRecommendation,
    EcoRecommendations,
    RoutePlan,
    SavingsReport,
    SavingsSnapshotResponse,
    SchoolClassStanding,
    WriteOffCreate,
    WriteOffResponse,
)
from app.security import require_dispatcher_key
from app.services.device_activity import (
    DeviceInactiveError,
    ensure_municipal_device_is_active,
)
from app.services.eco_advisor import (
    build_facts,
    drop_ungrounded,
    fallback_recommendations,
)
from app.services.eco_business import forecast_write_offs, school_standings
from app.services.eco_forecast import forecast_all
from app.services.eco_route import build_route_plan
from app.services.eco_savings import (
    ProfileNotConfiguredError,
    apply_profile_update,
    build_savings_report,
    get_profile,
    report_period,
)
from app.services.gemini_bot import gemini_bot


logger = logging.getLogger(__name__)

# The report itself is aggregated city data without personal information, so
# residents can see it. Everything that changes economics stays behind the key.
public_router = APIRouter(prefix="/api/eco", tags=["eco"])
router = APIRouter(
    prefix="/api/eco",
    tags=["eco"],
    dependencies=[Depends(require_dispatcher_key)],
)


def _profile_or_404(db: Session, profile_id: int | None = None) -> CostProfile:
    try:
        return get_profile(db, profile_id)
    except ProfileNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Экономический профиль не настроен",
        ) from exc


@public_router.get("/savings", response_model=SavingsReport)
def savings(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> SavingsReport:
    """Trips, fuel, money and CO2 saved against the fixed collection schedule."""

    profile = _profile_or_404(db, profile_id)
    period_start, period_end = report_period(days)
    try:
        return build_savings_report(db, profile, period_start, period_end)
    except SQLAlchemyError as exc:
        logger.exception("Could not build savings report profile_id=%s", profile.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Savings report is temporarily unavailable",
        ) from exc


@public_router.get("/forecast", response_model=list[ContainerForecast])
def forecast(
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[ContainerForecast]:
    """When each site reaches the dispatch threshold, most urgent first."""

    return forecast_all(db, _profile_or_404(db, profile_id))


@public_router.get("/schools/leaderboard", response_model=list[SchoolClassStanding])
def schools_leaderboard(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[SchoolClassStanding]:
    return school_standings(db, _profile_or_404(db, profile_id), limit=limit)


@router.get("/route", response_model=RoutePlan)
def route(
    horizon_hours: Annotated[float, Query(gt=0, le=168)] = 24.0,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> RoutePlan:
    """Tomorrow's round, priced against driving every site in the district."""

    profile = _profile_or_404(db, profile_id)
    return build_route_plan(db, profile, horizon_hours=horizon_hours)


def _parse_recommendations(raw: str) -> list[EcoRecommendation]:
    """Read the model's JSON answer, tolerating a markdown code fence."""

    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        _, _, text = text.partition("\n")
    try:
        payload = json.loads(text)
        items = payload["recommendations"]
    except (ValueError, KeyError, TypeError):
        logger.warning("Assistant returned an unreadable recommendation payload")
        return []

    parsed: list[EcoRecommendation] = []
    for item in items if isinstance(items, list) else []:
        try:
            parsed.append(EcoRecommendation.model_validate(item))
        except ValidationError:
            logger.warning("Skipped a malformed recommendation item")
    return parsed


@router.get("/recommendations", response_model=EcoRecommendations)
async def recommendations(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    horizon_hours: Annotated[float, Query(gt=0, le=168)] = 24.0,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> EcoRecommendations:
    """Three actions for tomorrow, derived from the computed metrics.

    The assistant never sees the database and never does arithmetic: it is
    handed the finished numbers and asked to interpret them. Anything it
    writes that quotes a number it was not given is dropped here, and the
    same facts are returned so that check can be repeated.
    """

    profile = _profile_or_404(db, profile_id)
    facts = build_facts(db, profile, days=days, horizon_hours=horizon_hours)

    generated = await gemini_bot.interpret_metrics(facts)
    if generated is not None:
        raw, model_name = generated
        grounded = drop_ungrounded(_parse_recommendations(raw), facts)
        if grounded:
            return EcoRecommendations(
                generated_at=utcnow(),
                provider="google-gemini",
                model=model_name,
                facts=facts,
                recommendations=grounded,
            )
        logger.warning(
            "No grounded recommendation survived verification; using local rules"
        )

    return EcoRecommendations(
        generated_at=utcnow(),
        provider="offline-fallback",
        model=None,
        facts=facts,
        recommendations=fallback_recommendations(facts),
    )


@router.get("/business/forecast", response_model=BusinessForecast)
def business_forecast(
    target: Annotated[date | None, Query()] = None,
    weeks: Annotated[int, Query(ge=1, le=12)] = 4,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> BusinessForecast:
    """Expected leftovers per product, averaged over the same weekday."""

    profile = _profile_or_404(db, profile_id)
    target_date = target or (utcnow().date() + timedelta(days=1))
    return forecast_write_offs(db, profile, target=target_date, weeks=weeks)


@router.get("/profile", response_model=EcoCostProfileResponse)
def read_profile(
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> EcoCostProfileResponse:
    return EcoCostProfileResponse.model_validate(_profile_or_404(db, profile_id))


@router.put("/profile", response_model=EcoCostProfileResponse)
def update_profile(
    payload: EcoCostProfileUpdate,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> EcoCostProfileResponse:
    """Tune the economics without redeploying: fuel prices and crew rates move."""

    profile = _profile_or_404(db, profile_id)
    if not apply_profile_update(profile, payload):
        return EcoCostProfileResponse.model_validate(profile)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not update cost profile id=%s", profile.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cost profile could not be updated",
        ) from exc

    db.refresh(profile)
    return EcoCostProfileResponse.model_validate(profile)


@router.get("/collections", response_model=list[CollectionEventResponse])
def list_collections(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: Session = Depends(get_db),
) -> list[CollectionEventResponse]:
    events = db.scalars(
        select(CollectionEvent)
        .order_by(CollectionEvent.collected_at.desc(), CollectionEvent.id.desc())
        .limit(limit)
    ).all()
    return [CollectionEventResponse.model_validate(event) for event in events]


@router.post(
    "/collections",
    response_model=CollectionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_collection(
    payload: CollectionEventCreate,
    db: Session = Depends(get_db),
) -> CollectionEventResponse:
    """Record a servicing the sensor could not see — an offline bin, a manual run.

    Telemetry detects emptying on its own; this endpoint keeps the record
    complete when a device was down or has no sensor at all.
    """

    try:
        ensure_municipal_device_is_active(db, payload.device_id)
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=409, detail="Device is inactive") from exc

    existing = db.scalar(
        select(CollectionEvent).where(
            CollectionEvent.idempotency_key == payload.idempotency_key
        )
    )
    if existing is not None:
        return CollectionEventResponse.model_validate(existing)

    device = db.get(Device, payload.device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )

    container = db.scalar(
        select(BinContainer).where(BinContainer.device_id == payload.device_id)
    )
    fill_before = container.last_fill_level if container is not None else 0.0
    event = CollectionEvent(
        device_id=payload.device_id,
        container_id=container.id if container is not None else None,
        collected_at=payload.collected_at or utcnow(),
        fill_ema_before_percent=fill_before,
        fill_raw_before_percent=fill_before,
        source="DISPATCHER",
        idempotency_key=payload.idempotency_key,
    )

    try:
        db.add(event)
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = db.scalar(
            select(CollectionEvent).where(
                CollectionEvent.idempotency_key == payload.idempotency_key
            )
        )
        if replay is None:
            raise
        return CollectionEventResponse.model_validate(replay)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not register collection device=%s", payload.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Collection event could not be stored",
        ) from exc

    db.refresh(event)
    return CollectionEventResponse.model_validate(event)


@router.post(
    "/snapshots",
    response_model=SavingsSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> SavingsSnapshotResponse:
    """Freeze the current report so a reported figure stays auditable later."""

    profile = _profile_or_404(db, profile_id)
    period_start, period_end = report_period(days)
    report = build_savings_report(db, profile, period_start, period_end)

    snapshot = SavingsSnapshot(
        profile_id=profile.id,
        period_start=report.period_start,
        period_end=report.period_end,
        containers=report.containers,
        trips_baseline=report.trips.baseline,
        trips_actual=report.trips.actual,
        trips_saved=report.trips.saved,
        km_saved=report.resources.km_saved,
        liters_saved=report.resources.liters_saved,
        kzt_saved=report.money.total_kzt,
        co2_kg_saved=report.resources.co2_kg_saved,
        bread_kg_saved=report.bread.kg_total,
        bread_kzt_saved=report.bread.rescued_value_kzt,
        payload=report.model_dump(mode="json"),
    )

    try:
        db.add(snapshot)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not store savings snapshot profile_id=%s", profile.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Savings snapshot could not be stored",
        ) from exc

    db.refresh(snapshot)
    return SavingsSnapshotResponse.model_validate(snapshot)


@router.get("/snapshots", response_model=list[SavingsSnapshotResponse])
def list_snapshots(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: Session = Depends(get_db),
) -> list[SavingsSnapshotResponse]:
    snapshots = db.scalars(
        select(SavingsSnapshot)
        .order_by(SavingsSnapshot.created_at.desc(), SavingsSnapshot.id.desc())
        .limit(limit)
    ).all()
    return [SavingsSnapshotResponse.model_validate(row) for row in snapshots]


@router.put("/write-offs", response_model=WriteOffResponse)
def upsert_write_off(
    payload: WriteOffCreate,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> WriteOffResponse:
    """Daily unsold-product log of a bakery, cafe or canteen.

    One record per product per day: sending the same day twice corrects the
    figures instead of double-counting them.
    """

    profile = _profile_or_404(db, profile_id)
    record = db.scalar(
        select(WriteOffRecord).where(
            WriteOffRecord.profile_id == profile.id,
            WriteOffRecord.occurred_on == payload.occurred_on,
            WriteOffRecord.product == payload.product,
        )
    )

    try:
        if record is None:
            record = WriteOffRecord(
                profile_id=profile.id,
                occurred_on=payload.occurred_on,
                product=payload.product,
                kg_written_off=payload.kg_written_off,
                kg_donated=payload.kg_donated,
                cost_kzt_per_kg=payload.cost_kzt_per_kg,
            )
            db.add(record)
        else:
            record.kg_written_off = payload.kg_written_off
            record.kg_donated = payload.kg_donated
            record.cost_kzt_per_kg = payload.cost_kzt_per_kg
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not store write-off profile_id=%s", profile.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Write-off record could not be stored",
        ) from exc

    db.refresh(record)
    return WriteOffResponse.model_validate(record)


@router.get("/write-offs", response_model=list[WriteOffResponse])
def list_write_offs(
    limit: Annotated[int, Query(ge=1, le=365)] = 60,
    profile_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[WriteOffResponse]:
    profile = _profile_or_404(db, profile_id)
    records = db.scalars(
        select(WriteOffRecord)
        .where(WriteOffRecord.profile_id == profile.id)
        .order_by(WriteOffRecord.occurred_on.desc(), WriteOffRecord.id.desc())
        .limit(limit)
    ).all()
    return [WriteOffResponse.model_validate(row) for row in records]
