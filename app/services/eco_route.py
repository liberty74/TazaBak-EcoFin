"""Which sites to visit tomorrow, and what skipping the rest is worth.

The planner answers with two numbers side by side: the distance of driving the
whole district and the distance of driving only what the forecast says is due.
The gap between them, converted to fuel and money, is the product.

Both figures come from the same algorithm on the same road model, so the
comparison is not rigged by measuring the two routes differently.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models import CostProfile, utcnow
from app.schemas import ContainerForecast, RouteLeg, RoutePlan, RouteScenario
from app.services.eco_forecast import forecast_all


EARTH_RADIUS_KM = 6371.0
# Straight-line distance understates real driving. The factor is the usual
# planning correction for a city grid and is applied to both scenarios alike.
ROAD_WINDING_FACTOR = 1.3


@dataclass(frozen=True, slots=True)
class Point:
    label: str
    latitude: float
    longitude: float
    container_id: int | None = None


def haversine_km(first: Point, second: Point) -> float:
    """Great-circle distance between two coordinates."""

    lat1, lon1 = radians(first.latitude), radians(first.longitude)
    lat2, lon2 = radians(second.latitude), radians(second.longitude)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    inner = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(inner))


def tour_length_km(points: list[Point]) -> float:
    """Length of a closed tour that starts and ends at the first point."""

    if len(points) < 2:
        return 0.0
    legs = zip(points, points[1:] + [points[0]])
    return sum(haversine_km(origin, destination) for origin, destination in legs)


def nearest_neighbour(depot: Point, stops: list[Point]) -> list[Point]:
    """Greedy tour: from where you are, go to the closest place left."""

    remaining = list(stops)
    order = [depot]
    current = depot
    while remaining:
        nearest = min(remaining, key=lambda stop: haversine_km(current, stop))
        remaining.remove(nearest)
        order.append(nearest)
        current = nearest
    return order


def two_opt(order: list[Point], *, max_passes: int = 40) -> list[Point]:
    """Untangle a greedy tour by reversing segments while that shortens it.

    The depot stays first: it is where the truck is, not a stop to reorder.
    """

    if len(order) < 4:
        return order

    best = list(order)
    best_length = tour_length_km(best)
    for _ in range(max_passes):
        improved = False
        for left in range(1, len(best) - 1):
            for right in range(left + 1, len(best)):
                candidate = (
                    best[:left] + best[left : right + 1][::-1] + best[right + 1 :]
                )
                candidate_length = tour_length_km(candidate)
                if candidate_length < best_length - 1e-9:
                    best, best_length = candidate, candidate_length
                    improved = True
        if not improved:
            break
    return best


def _scenario(
    depot: Point, stops: list[Point], profile: CostProfile, label: str
) -> tuple[RouteScenario, list[Point]]:
    if not stops:
        return (
            RouteScenario(label=label, stops=0, distance_km=0.0, liters=0.0, kzt=0.0),
            [depot],
        )

    order = two_opt(nearest_neighbour(depot, stops))
    distance = tour_length_km(order) * ROAD_WINDING_FACTOR
    liters = distance / 100.0 * profile.fuel_consumption_l_per_100km
    crew_kzt = len(stops) * profile.minutes_per_stop / 60.0 * profile.crew_cost_kzt_per_hour
    kzt = liters * profile.fuel_price_kzt_per_liter + crew_kzt

    return (
        RouteScenario(
            label=label,
            stops=len(stops),
            distance_km=round(distance, 2),
            liters=round(liters, 2),
            kzt=round(kzt, 2),
        ),
        order,
    )


def build_route_plan(
    db: Session,
    profile: CostProfile,
    *,
    horizon_hours: float = 24.0,
) -> RoutePlan:
    """Plan tomorrow's round and price it against driving every site."""

    depot = Point(label="Автобаза", latitude=profile.depot_latitude, longitude=profile.depot_longitude)
    forecasts = forecast_all(db, profile)

    all_stops = [
        Point(
            label=item.name,
            latitude=item.latitude,
            longitude=item.longitude,
            container_id=item.container_id,
        )
        for item in forecasts
    ]
    due: list[ContainerForecast] = [
        item
        for item in forecasts
        if item.status == "due_now"
        or (item.eta_hours is not None and item.eta_hours <= horizon_hours)
    ]
    due_stops = [
        Point(
            label=item.name,
            latitude=item.latitude,
            longitude=item.longitude,
            container_id=item.container_id,
        )
        for item in due
    ]

    baseline_scenario, _ = _scenario(depot, all_stops, profile, "Объехать все площадки")
    planned_scenario, planned_order = _scenario(
        depot, due_stops, profile, "По плану TazaBAK"
    )

    legs: list[RouteLeg] = []
    for position, (origin, destination) in enumerate(
        zip(planned_order, planned_order[1:] + [depot]), start=1
    ):
        legs.append(
            RouteLeg(
                position=position,
                from_label=origin.label,
                to_label=destination.label,
                container_id=destination.container_id,
                distance_km=round(
                    haversine_km(origin, destination) * ROAD_WINDING_FACTOR, 2
                ),
            )
        )

    liters_saved = max(0.0, baseline_scenario.liters - planned_scenario.liters)
    return RoutePlan(
        generated_at=utcnow(),
        horizon_hours=horizon_hours,
        baseline=baseline_scenario,
        planned=planned_scenario,
        distance_saved_km=round(
            max(0.0, baseline_scenario.distance_km - planned_scenario.distance_km), 2
        ),
        liters_saved=round(liters_saved, 2),
        kzt_saved=round(max(0.0, baseline_scenario.kzt - planned_scenario.kzt), 2),
        co2_kg_saved=round(liters_saved * profile.co2_kg_per_liter, 2),
        legs=legs,
        skipped=[
            item.name
            for item in forecasts
            if item.container_id not in {stop.container_id for stop in due_stops}
        ],
    )
