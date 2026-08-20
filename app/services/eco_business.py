"""Small-business side of EcoFin.

A bakery does not care about refuse routes. Its money leaks in the evening,
when unsold bread is written off — the exact problem the Astana interview
described. Demand there is weekly, not daily: Tuesday resembles last Tuesday
far more than it resembles yesterday, so the forecast averages the same
weekday instead of a rolling window across all days.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CostProfile, WriteOffRecord
from app.schemas import BusinessForecast, ProductForecast, WeekdayProfile


WEEKDAY_NAMES = (
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
)
DEFAULT_LOOKBACK_WEEKS = 4


def _records_for_lookback(
    db: Session, profile: CostProfile, target: date, weeks: int
) -> list[WriteOffRecord]:
    earliest = target - timedelta(weeks=weeks)
    return list(
        db.scalars(
            select(WriteOffRecord)
            .where(
                WriteOffRecord.profile_id == profile.id,
                WriteOffRecord.occurred_on >= earliest,
                WriteOffRecord.occurred_on < target,
            )
            .order_by(WriteOffRecord.occurred_on.asc())
        ).all()
    )


def forecast_write_offs(
    db: Session,
    profile: CostProfile,
    *,
    target: date,
    weeks: int = DEFAULT_LOOKBACK_WEEKS,
) -> BusinessForecast:
    """Predict tomorrow's leftovers per product from the same weekday history."""

    records = _records_for_lookback(db, profile, target, weeks)
    target_weekday = target.weekday()

    per_product_same_weekday: dict[str, list[float]] = defaultdict(list)
    per_product_all_days: dict[str, list[float]] = defaultdict(list)
    per_weekday: dict[int, list[float]] = defaultdict(list)

    for record in records:
        per_product_all_days[record.product].append(record.kg_written_off)
        per_weekday[record.occurred_on.weekday()].append(record.kg_written_off)
        if record.occurred_on.weekday() == target_weekday:
            per_product_same_weekday[record.product].append(record.kg_written_off)

    products: list[ProductForecast] = []
    for product, all_values in sorted(per_product_all_days.items()):
        same_weekday = per_product_same_weekday.get(product, [])
        overall_average = sum(all_values) / len(all_values)
        if same_weekday:
            expected = sum(same_weekday) / len(same_weekday)
            basis = "same_weekday"
        else:
            # Not enough history for this weekday yet: fall back to the overall
            # average and say so, rather than pretending the sample exists.
            expected = overall_average
            basis = "all_days"
        deviation = (
            (expected - overall_average) / overall_average * 100.0
            if overall_average > 0
            else 0.0
        )
        products.append(
            ProductForecast(
                product=product,
                expected_kg=round(expected, 2),
                average_kg=round(overall_average, 2),
                deviation_percent=round(deviation, 1),
                samples=len(same_weekday) if same_weekday else len(all_values),
                basis=basis,
            )
        )

    weekday_profile = [
        WeekdayProfile(
            weekday=index,
            name=WEEKDAY_NAMES[index],
            average_kg=round(sum(values) / len(values), 2),
            samples=len(values),
        )
        for index, values in sorted(per_weekday.items())
    ]

    total_written = sum(record.kg_written_off for record in records)
    total_donated = sum(record.kg_donated for record in records)
    rescued_value = sum(
        record.kg_donated * record.cost_kzt_per_kg for record in records
    )

    return BusinessForecast(
        profile_id=profile.id,
        org_name=profile.org_name,
        target_date=target,
        target_weekday=WEEKDAY_NAMES[target_weekday],
        lookback_weeks=weeks,
        products=products,
        weekday_profile=weekday_profile,
        history_days=len({record.occurred_on for record in records}),
        total_written_off_kg=round(total_written, 2),
        total_donated_kg=round(total_donated, 2),
        donation_rate_percent=(
            round(total_donated / total_written * 100.0, 1) if total_written > 0 else 0.0
        ),
        rescued_value_kzt=round(rescued_value, 2),
    )
