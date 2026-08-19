"""EcoFin economics: skipped stops converted into fuel, money and CO2.

The model is marginal on purpose. A refuse truck serves many container sites
on one route, so skipping a site does not save a round trip from the depot —
it saves the leg to the next stop and the crew time spent servicing it. Using
a whole trip per container would inflate the result several times over, and
the first jury question would break the number.

Everything reported here is derived from two measured facts: how often the
site was actually serviced (``CollectionEvent``) and what the schedule it
replaces would have cost (``CostProfile.baseline_trips_per_week``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BinContainer,
    BioAnalysis,
    CollectionEvent,
    CostProfile,
    Device,
    WriteOffRecord,
    utcnow,
)
from app.schemas import (
    EcoBread,
    EcoCostProfileUpdate,
    EcoFormulaInputs,
    EcoMoney,
    EcoPayback,
    EcoResources,
    EcoTrips,
    EcoWeeklyPoint,
    SavingsReport,
)


DAYS_PER_WEEK = 7.0
DAYS_PER_MONTH = 30.0


class ProfileNotConfiguredError(RuntimeError):
    """Raised when no economic profile exists to calculate against."""


@dataclass(frozen=True, slots=True)
class StopCost:
    """What one skipped servicing of a container site is worth."""

    km: float
    liters: float
    fuel_kzt: float
    crew_kzt: float

    @property
    def total_kzt(self) -> float:
        return self.fuel_kzt + self.crew_kzt


def get_profile(db: Session, profile_id: int | None = None) -> CostProfile:
    """Return the requested profile, or the default one for the operator."""

    if profile_id is not None:
        profile = db.get(CostProfile, profile_id)
        if profile is None:
            raise ProfileNotConfiguredError(f"Cost profile {profile_id} not found")
        return profile

    profile = db.scalar(
        select(CostProfile)
        .order_by(CostProfile.is_default.desc(), CostProfile.id.asc())
        .limit(1)
    )
    if profile is None:
        raise ProfileNotConfiguredError("No cost profile is configured")
    return profile


def apply_profile_update(profile: CostProfile, update: EcoCostProfileUpdate) -> bool:
    """Copy the supplied fields onto the profile; report whether it changed."""

    changed = False
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if getattr(profile, field) != value:
            setattr(profile, field, value)
            changed = True
    return changed


def stop_cost(profile: CostProfile) -> StopCost:
    """Fuel and crew cost of servicing one container site."""

    km = profile.km_per_stop
    liters = km / 100.0 * profile.fuel_consumption_l_per_100km
    fuel_kzt = liters * profile.fuel_price_kzt_per_liter
    crew_kzt = profile.minutes_per_stop / 60.0 * profile.crew_cost_kzt_per_hour
    return StopCost(km=km, liters=liters, fuel_kzt=fuel_kzt, crew_kzt=crew_kzt)


def active_container_device_ids(db: Session) -> list[str]:
    """Municipal sites only: bread boxes are not served by a refuse truck."""

    return list(
        db.scalars(
            select(BinContainer.device_id)
            .join(Device, Device.id == BinContainer.device_id)
            .where(BinContainer.is_active.is_(True), Device.kind == "municipal")
            .order_by(BinContainer.id.asc())
        ).all()
    )


def _baseline_trips(
    profile: CostProfile, days: float, container_count: int
) -> float:
    """Trips the fixed schedule would have produced over the period."""

    if days <= 0 or container_count <= 0:
        return 0.0
    return days / DAYS_PER_WEEK * profile.baseline_trips_per_week * container_count


def _count_collections(
    db: Session,
    device_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> int:
    if not device_ids:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(CollectionEvent)
            .where(
                CollectionEvent.device_id.in_(device_ids),
                CollectionEvent.collected_at >= period_start,
                CollectionEvent.collected_at < period_end,
            )
        )
        or 0
    )


def _average_fill_at_collection(
    db: Session,
    device_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> float | None:
    """The Sensoneo benchmark in our own data: how full bins really were."""

    if not device_ids:
        return None
    average = db.scalar(
        select(func.avg(CollectionEvent.fill_ema_before_percent)).where(
            CollectionEvent.device_id.in_(device_ids),
            CollectionEvent.collected_at >= period_start,
            CollectionEvent.collected_at < period_end,
        )
    )
    return round(float(average), 2) if average is not None else None


def _weekly_breakdown(
    db: Session,
    profile: CostProfile,
    device_ids: list[str],
    period_start: datetime,
    period_end: datetime,
    cost: StopCost,
) -> list[EcoWeeklyPoint]:
    """Seven-day buckets for the savings chart; the last one may be partial."""

    points: list[EcoWeeklyPoint] = []
    bucket_start = period_start
    while bucket_start < period_end:
        bucket_end = min(bucket_start + timedelta(days=7), period_end)
        bucket_days = (bucket_end - bucket_start).total_seconds() / 86400.0
        baseline = _baseline_trips(profile, bucket_days, len(device_ids))
        actual = _count_collections(db, device_ids, bucket_start, bucket_end)
        saved = max(0.0, baseline - actual)
        points.append(
            EcoWeeklyPoint(
                week_start=bucket_start.date(),
                trips_saved=round(saved, 2),
                kzt_saved=round(saved * cost.total_kzt, 2),
                co2_kg_saved=round(
                    saved * cost.liters * profile.co2_kg_per_liter, 2
                ),
                # Неполная неделя набирает меньше экономии просто потому, что
                # ещё идёт. Помечаем, чтобы её не сравнивали с полными.
                is_partial=bucket_days < 7.0 - 1e-9,
            )
        )
        bucket_start = bucket_end
    return points


def _bread_saved(
    db: Session,
    profile: CostProfile,
    period_start: datetime,
    period_end: datetime,
) -> EcoBread:
    """Bread kept out of the bin, from citizens' scans and business logs."""

    approved = int(
        db.scalar(
            select(func.count())
            .select_from(BioAnalysis)
            .where(
                BioAnalysis.status == "approve",
                BioAnalysis.created_at >= period_start,
                BioAnalysis.created_at < period_end,
            )
        )
        or 0
    )
    kg_from_citizens = approved * profile.bread_avg_weight_kg

    # Each write-off carries its own cost per kilogram: a baguette is not
    # priced like a loaf, so the business side is valued record by record.
    business_rows = db.execute(
        select(WriteOffRecord.kg_donated, WriteOffRecord.cost_kzt_per_kg).where(
            WriteOffRecord.profile_id == profile.id,
            WriteOffRecord.occurred_on >= period_start.date(),
            WriteOffRecord.occurred_on <= period_end.date(),
        )
    ).all()
    kg_from_business = sum(float(kg) for kg, _ in business_rows)
    business_value = sum(float(kg) * float(cost) for kg, cost in business_rows)

    kg_total = kg_from_citizens + kg_from_business
    rescued_value = kg_from_citizens * profile.bread_cost_kzt_per_kg + business_value

    return EcoBread(
        kg_from_citizens=round(kg_from_citizens, 2),
        kg_from_business=round(kg_from_business, 2),
        kg_total=round(kg_total, 2),
        rescued_value_kzt=round(rescued_value, 2),
    )


def _payback(
    profile: CostProfile,
    container_count: int,
    total_kzt: float,
    days: float,
) -> EcoPayback:
    """How long the hardware takes to pay for itself at the current rate.

    Subscription revenue is a cost for the client, so it is subtracted before
    the payback period is derived. When savings do not cover the subscription
    the period is undefined rather than negative or infinite.
    """

    monthly_savings = total_kzt / days * DAYS_PER_MONTH if days > 0 else 0.0
    monthly_subscription = profile.subscription_kzt_per_month * container_count
    net_monthly = monthly_savings - monthly_subscription
    install_total = profile.install_price_kzt * container_count
    payback_months = (
        install_total / net_monthly if net_monthly > 0 and install_total > 0 else None
    )
    return EcoPayback(
        monthly_savings_kzt=round(monthly_savings, 2),
        monthly_subscription_kzt=round(monthly_subscription, 2),
        net_monthly_kzt=round(net_monthly, 2),
        install_total_kzt=round(install_total, 2),
        payback_months=round(payback_months, 1) if payback_months is not None else None,
    )


def build_savings_report(
    db: Session,
    profile: CostProfile,
    period_start: datetime,
    period_end: datetime,
) -> SavingsReport:
    """Calculate the full EcoFin report for one operator over one period."""

    if period_end <= period_start:
        raise ValueError("period_end must be later than period_start")

    device_ids = active_container_device_ids(db)
    container_count = len(device_ids)
    days = (period_end - period_start).total_seconds() / 86400.0
    cost = stop_cost(profile)

    baseline = _baseline_trips(profile, days, container_count)
    actual = _count_collections(db, device_ids, period_start, period_end)
    # Servicing more often than the schedule is not a negative saving: it just
    # means nothing was saved that period.
    saved = max(0.0, baseline - actual)
    reduction_percent = (saved / baseline * 100.0) if baseline > 0 else 0.0

    km_saved = saved * cost.km
    liters_saved = saved * cost.liters
    fuel_kzt = saved * cost.fuel_kzt
    crew_kzt = saved * cost.crew_kzt
    total_kzt = fuel_kzt + crew_kzt

    return SavingsReport(
        generated_at=utcnow(),
        period_start=period_start,
        period_end=period_end,
        profile_id=profile.id,
        org_name=profile.org_name,
        city=profile.city,
        containers=container_count,
        trips=EcoTrips(
            baseline=round(baseline, 2),
            actual=actual,
            saved=round(saved, 2),
            reduction_percent=round(reduction_percent, 2),
            average_fill_at_collection_percent=_average_fill_at_collection(
                db, device_ids, period_start, period_end
            ),
        ),
        resources=EcoResources(
            km_saved=round(km_saved, 2),
            liters_saved=round(liters_saved, 2),
            co2_kg_saved=round(liters_saved * profile.co2_kg_per_liter, 2),
        ),
        money=EcoMoney(
            fuel_kzt=round(fuel_kzt, 2),
            crew_kzt=round(crew_kzt, 2),
            total_kzt=round(total_kzt, 2),
        ),
        bread=_bread_saved(db, profile, period_start, period_end),
        payback=_payback(profile, container_count, total_kzt, days),
        weekly=_weekly_breakdown(
            db, profile, device_ids, period_start, period_end, cost
        ),
        formula=EcoFormulaInputs(
            days=round(days, 3),
            containers=container_count,
            km_per_stop=profile.km_per_stop,
            minutes_per_stop=profile.minutes_per_stop,
            fuel_consumption_l_per_100km=profile.fuel_consumption_l_per_100km,
            fuel_price_kzt_per_liter=profile.fuel_price_kzt_per_liter,
            crew_cost_kzt_per_hour=profile.crew_cost_kzt_per_hour,
            baseline_trips_per_week=profile.baseline_trips_per_week,
            co2_kg_per_liter=profile.co2_kg_per_liter,
            km_per_saved_stop=round(cost.km, 4),
            liters_per_saved_stop=round(cost.liters, 4),
            kzt_per_saved_stop=round(cost.total_kzt, 4),
        ),
    )


def report_period(days: int, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Half-open reporting window ending at the current moment."""

    period_end = now or utcnow()
    return period_end - timedelta(days=days), period_end
