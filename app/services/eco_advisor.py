"""Recommendations built on computed metrics, not on the model's memory.

The assistant is an interpreter here, not a source of facts. Everything it is
allowed to talk about is calculated first by the EcoFin engines and handed to
it as JSON; the language model only turns those numbers into actions.

That claim is not left to trust. Every number the model writes is checked
against the numbers it was given, and a recommendation containing anything
else is discarded before it reaches the dispatcher. The same facts are
returned with the answer, so the check can be repeated by hand.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import CostProfile, utcnow
from app.schemas import EcoRecommendation
from app.services.eco_business import forecast_write_offs
from app.services.eco_forecast import forecast_all
from app.services.eco_route import build_route_plan
from app.services.eco_savings import build_savings_report, report_period


logger = logging.getLogger(__name__)


# Long lists cost tokens and add nothing: a dispatcher acts on the urgent few.
MAX_LISTED_CONTAINERS = 5
MAX_LISTED_PRODUCTS = 3

_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")


def build_facts(
    db: Session,
    profile: CostProfile,
    *,
    days: int = 30,
    horizon_hours: float = 24.0,
) -> dict[str, Any]:
    """Collect everything the assistant is allowed to reason about."""

    period_start, period_end = report_period(days)
    report = build_savings_report(db, profile, period_start, period_end)
    route = build_route_plan(db, profile, horizon_hours=horizon_hours)
    forecasts = forecast_all(db, profile)
    bakery = forecast_write_offs(
        db, profile, target=utcnow().date() + timedelta(days=1)
    )

    due = [
        {
            "name": item.name,
            "fill_percent": item.fill_percent,
            "eta_hours": item.eta_hours,
        }
        for item in forecasts
        if item.status == "due_now"
        or (item.eta_hours is not None and item.eta_hours <= horizon_hours)
    ][:MAX_LISTED_CONTAINERS]

    return {
        "city": profile.city,
        "period_days": days,
        "containers": report.containers,
        "trips": {
            "baseline": report.trips.baseline,
            "actual": report.trips.actual,
            "saved": report.trips.saved,
            "reduction_percent": report.trips.reduction_percent,
            "average_fill_at_collection_percent": (
                report.trips.average_fill_at_collection_percent
            ),
        },
        "resources": {
            "km_saved": report.resources.km_saved,
            "liters_saved": report.resources.liters_saved,
            "co2_kg_saved": report.resources.co2_kg_saved,
        },
        "money": {
            "saved_kzt": report.money.total_kzt,
            "monthly_savings_kzt": report.payback.monthly_savings_kzt,
            "monthly_subscription_kzt": report.payback.monthly_subscription_kzt,
            "net_monthly_kzt": report.payback.net_monthly_kzt,
            "payback_months": report.payback.payback_months,
        },
        "route_next_hours": {
            "horizon_hours": route.horizon_hours,
            "stops_planned": route.planned.stops,
            "stops_if_driving_everything": route.baseline.stops,
            "km_planned": route.planned.distance_km,
            "km_if_driving_everything": route.baseline.distance_km,
            "kzt_saved": route.kzt_saved,
        },
        "containers_due": due,
        "bakery": {
            "target_date": bakery.target_date.isoformat(),
            "target_weekday": bakery.target_weekday,
            "donation_rate_percent": bakery.donation_rate_percent,
            "products": [
                {
                    "product": item.product,
                    "expected_kg": item.expected_kg,
                    "average_kg": item.average_kg,
                    "deviation_percent": item.deviation_percent,
                }
                for item in bakery.products[:MAX_LISTED_PRODUCTS]
            ],
        },
    }


def authorised_numbers(facts: dict[str, Any]) -> set[float]:
    """Every number the assistant was given, dates included."""

    serialized = json.dumps(facts, ensure_ascii=False)
    return {
        float(token.replace(",", "."))
        for token in _NUMBER_PATTERN.findall(serialized)
    }


def _is_authorised(value: float, authorised: set[float]) -> bool:
    for allowed in authorised:
        if value == allowed:
            return True
        # Rounding a figure that was supplied is presentation, not invention.
        if value in {float(round(allowed)), round(allowed, 1)}:
            return True
        if abs(value - allowed) <= abs(allowed) * 0.01:
            return True
    return False


def uses_only_authorised_numbers(text: str, authorised: set[float]) -> bool:
    """True when every number in the text came from the computed facts."""

    return all(
        _is_authorised(float(token.replace(",", ".")), authorised)
        for token in _NUMBER_PATTERN.findall(text)
    )


def drop_ungrounded(
    recommendations: list[EcoRecommendation], facts: dict[str, Any]
) -> list[EcoRecommendation]:
    """Remove any recommendation quoting a number it was not given."""

    authorised = authorised_numbers(facts)
    grounded: list[EcoRecommendation] = []
    for item in recommendations:
        if uses_only_authorised_numbers(f"{item.title} {item.detail}", authorised):
            grounded.append(item)
        else:
            logger.warning(
                "Discarded an ungrounded recommendation: %r", item.title
            )
    return grounded


def fallback_recommendations(facts: dict[str, Any]) -> list[EcoRecommendation]:
    """Advice derived from the same numbers without a language model.

    Used when Gemini has no key, no quota or no network. The figures are
    identical either way — only the wording is not generated.
    """

    route = facts["route_next_hours"]
    trips = facts["trips"]
    money = facts["money"]
    bakery = facts["bakery"]
    items: list[EcoRecommendation] = []

    skipped = route["stops_if_driving_everything"] - route["stops_planned"]
    if skipped > 0:
        items.append(
            EcoRecommendation(
                title=f"Выехать на {route['stops_planned']} площадки из {route['stops_if_driving_everything']}",
                detail=(
                    f"По прогнозу в ближайшие {route['horizon_hours']} часа порога "
                    f"достигают только {route['stops_planned']} площадки. Маршрут "
                    f"составит {route['km_planned']} км вместо {route['km_if_driving_everything']} км "
                    f"и сэкономит {route['kzt_saved']} ₸."
                ),
            )
        )

    average_fill = trips["average_fill_at_collection_percent"]
    if average_fill is not None:
        items.append(
            EcoRecommendation(
                title=f"Средняя заполненность при вывозе — {average_fill}%",
                detail=(
                    f"За {facts['period_days']} дней вывоз выполнен "
                    f"{trips['actual']} раз вместо {trips['baseline']} по графику: "
                    f"сэкономлено {money['saved_kzt']} ₸ и "
                    f"{facts['resources']['co2_kg_saved']} кг CO₂."
                ),
            )
        )

    products = bakery["products"]
    if products:
        leader = max(products, key=lambda item: item["expected_kg"])
        items.append(
            EcoRecommendation(
                title=f"Пекарня: на {bakery['target_weekday'].casefold()} ожидается {leader['expected_kg']} кг остатков",
                detail=(
                    f"Больше всего останется позиции «{leader['product']}» — "
                    f"{leader['expected_kg']} кг против среднего {leader['average_kg']} кг. "
                    f"Заранее согласуйте вывоз в приют: сейчас передаётся "
                    f"{bakery['donation_rate_percent']}% списаний."
                ),
            )
        )

    return items
