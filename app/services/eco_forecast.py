"""When a container will be full, and therefore when it is worth driving.

An alert says something has already happened. A forecast says a trip is not
needed yet — which is the part that actually saves money, so this is where the
optimisation advice of the EcoFin track comes from.

The trend is fitted with ordinary least squares written out by hand: the model
is three lines of arithmetic, it adds no dependency, and every step of it can
be reproduced on a whiteboard during the defence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BinContainer,
    CollectionEvent,
    CostProfile,
    Device,
    Telemetry,
    utcnow,
)
from app.schemas import ContainerForecast


# Two points always fit a line perfectly, which would report a confident trend
# from noise. Three is the smallest sample that can disagree with itself.
MIN_SAMPLES = 3
DEFAULT_WINDOW = 20


@dataclass(frozen=True, slots=True)
class Trend:
    """Least-squares fit of fill level against time."""

    rate_percent_per_hour: float
    r_squared: float
    samples: int


def fit_trend(points: list[tuple[float, float]]) -> Trend | None:
    """Fit ``fill = a + b * hours`` and report how well the line explains it.

    ``points`` are ``(hours_since_first_sample, fill_percent)`` pairs.
    """

    count = len(points)
    if count < MIN_SAMPLES:
        return None

    mean_x = sum(x for x, _ in points) / count
    mean_y = sum(y for _, y in points) / count

    covariance = sum((x - mean_x) * (y - mean_y) for x, y in points)
    variance_x = sum((x - mean_x) ** 2 for x, _ in points)
    if variance_x == 0:
        # Every reading carries the same timestamp: no time base, no trend.
        return None

    slope = covariance / variance_x
    intercept = mean_y - slope * mean_x

    total_variance = sum((y - mean_y) ** 2 for _, y in points)
    residuals = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    # A flat series is explained perfectly by a flat line.
    r_squared = 1.0 if total_variance == 0 else 1.0 - residuals / total_variance

    return Trend(
        rate_percent_per_hour=slope,
        r_squared=max(0.0, min(1.0, r_squared)),
        samples=count,
    )


def _last_collection_at(db: Session, device_id: str) -> datetime | None:
    return db.scalar(
        select(CollectionEvent.collected_at)
        .where(CollectionEvent.device_id == device_id)
        .order_by(CollectionEvent.collected_at.desc())
        .limit(1)
    )


def _recent_measurements(
    db: Session, device_id: str, window: int
) -> list[Telemetry]:
    """Readings of the current filling cycle, newest cycle only.

    Measurements from before the last collection describe a bin that no longer
    exists: fitting across the emptying step would produce a falling trend and
    an infinite forecast.
    """

    query = select(Telemetry).where(Telemetry.device_id == device_id)
    since = _last_collection_at(db, device_id)
    if since is not None:
        query = query.where(Telemetry.received_at > since)

    rows = db.scalars(
        query.order_by(Telemetry.received_at.desc(), Telemetry.id.desc()).limit(window)
    ).all()
    return list(reversed(rows))


def forecast_container(
    db: Session,
    profile: CostProfile,
    container: BinContainer,
    *,
    window: int = DEFAULT_WINDOW,
    now: datetime | None = None,
) -> ContainerForecast:
    """Estimate when one site reaches the dispatch threshold."""

    moment = now or utcnow()
    threshold = profile.fill_threshold_percent
    measurements = _recent_measurements(db, container.device_id, window)
    fill_now = (
        measurements[-1].fill_ema_percent if measurements else container.last_fill_level
    )

    base = ContainerForecast(
        container_id=container.id,
        device_id=container.device_id,
        name=container.name,
        latitude=container.latitude,
        longitude=container.longitude,
        fill_percent=round(fill_now, 2),
        threshold_percent=threshold,
        samples=len(measurements),
        status="unavailable",
    )

    if fill_now >= threshold:
        # Already due: no arithmetic can make the trip more urgent than now.
        return base.model_copy(
            update={"status": "due_now", "eta_hours": 0.0, "eta_at": moment}
        )

    if len(measurements) < MIN_SAMPLES:
        return base.model_copy(update={"reason": "not_enough_measurements"})

    first_at = measurements[0].received_at
    points = [
        ((row.received_at - first_at).total_seconds() / 3600.0, row.fill_ema_percent)
        for row in measurements
    ]
    trend = fit_trend(points)
    if trend is None:
        return base.model_copy(update={"reason": "not_enough_measurements"})

    if trend.rate_percent_per_hour <= 0:
        # A bin that is not filling has no arrival time. Reporting "never" is
        # honest; reporting a huge number would look like a real forecast.
        return base.model_copy(
            update={
                "reason": "not_filling",
                "rate_percent_per_hour": round(trend.rate_percent_per_hour, 4),
                "r_squared": round(trend.r_squared, 3),
            }
        )

    eta_hours = (threshold - fill_now) / trend.rate_percent_per_hour
    return base.model_copy(
        update={
            "status": "forecast",
            "rate_percent_per_hour": round(trend.rate_percent_per_hour, 4),
            "r_squared": round(trend.r_squared, 3),
            "eta_hours": round(eta_hours, 2),
            "eta_at": moment + timedelta(hours=eta_hours),
        }
    )


def forecast_all(
    db: Session,
    profile: CostProfile,
    *,
    window: int = DEFAULT_WINDOW,
    now: datetime | None = None,
) -> list[ContainerForecast]:
    """Forecast every active municipal site, most urgent first."""

    containers = db.scalars(
        select(BinContainer)
        .join(Device, Device.id == BinContainer.device_id)
        .where(BinContainer.is_active.is_(True), Device.kind == "municipal")
        .order_by(BinContainer.id.asc())
    ).all()

    forecasts = [
        forecast_container(db, profile, container, window=window, now=now)
        for container in containers
    ]
    # Due sites first, then the soonest arrival; sites without a trend last.
    forecasts.sort(
        key=lambda item: (
            item.eta_hours if item.eta_hours is not None else float("inf"),
            -item.fill_percent,
        )
    )
    return forecasts
