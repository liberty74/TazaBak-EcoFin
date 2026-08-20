"""Forecast, route planning and bakery leftovers."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import delete, select

from app.config import settings
from app.models import (
    BinContainer,
    CollectionEvent,
    Telemetry,
    WriteOffRecord,
    utcnow,
)
from app.services.eco_business import forecast_write_offs
from app.services.eco_forecast import fit_trend, forecast_container
from app.services.eco_route import (
    Point,
    haversine_km,
    nearest_neighbour,
    tour_length_km,
    two_opt,
)
from app.services.eco_savings import get_profile


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}
PROTOTYPE = "municipal-prototype-001"


def _add_measurements(db, device_id: str, series: list[tuple[float, float]]) -> None:
    """Insert ``(hours_ago, fill_percent)`` readings for one device."""

    now = utcnow()
    for hours_ago, fill in series:
        moment = now - timedelta(hours=hours_ago)
        db.add(
            Telemetry(
                device_id=device_id,
                distance_cm=25.0 - fill / 100.0 * 18.0,
                temp_in_c=20.0,
                temp_out_c=18.0,
                temperature_delta_c=2.0,
                delta_rate_c_per_sec=0.0,
                sampling_interval_seconds=3600.0,
                fill_raw_percent=fill,
                fill_ema_percent=fill,
                fire_score=1.4,
                fire_streak=0,
                measured_at=moment,
                received_at=moment,
            )
        )
    db.commit()


def _prototype(db) -> BinContainer:
    container = db.scalar(
        select(BinContainer).where(BinContainer.device_id == PROTOTYPE)
    )
    assert container is not None
    return container


# --- Least squares ---------------------------------------------------------


def test_trend_recovers_a_known_slope_exactly() -> None:
    # Ровно 2 % в час, без шума: наклон обязан совпасть до знака после запятой.
    trend = fit_trend([(0.0, 10.0), (1.0, 12.0), (2.0, 14.0), (3.0, 16.0)])

    assert trend is not None
    assert trend.rate_percent_per_hour == pytest.approx(2.0)
    assert trend.r_squared == pytest.approx(1.0)
    assert trend.samples == 4


def test_trend_needs_at_least_three_points() -> None:
    # Через две точки всегда проходит идеальная прямая — это не тренд.
    assert fit_trend([(0.0, 10.0), (1.0, 20.0)]) is None


def test_trend_reports_low_confidence_on_noise() -> None:
    noisy = fit_trend([(0.0, 50.0), (1.0, 10.0), (2.0, 90.0), (3.0, 20.0)])

    assert noisy is not None
    assert noisy.r_squared < 0.3


def test_trend_without_time_spread_is_rejected() -> None:
    assert fit_trend([(5.0, 10.0), (5.0, 20.0), (5.0, 30.0)]) is None


# --- Container forecast ----------------------------------------------------


def test_forecast_estimates_arrival_at_the_threshold(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        profile.fill_threshold_percent = 80.0
        db.commit()

        # 50 % сейчас, рост 2 % в час → до 80 % остаётся 15 часов.
        _add_measurements(db, PROTOTYPE, [(6, 38.0), (4, 42.0), (2, 46.0), (0, 50.0)])
        result = forecast_container(db, profile, _prototype(db))

    assert result.status == "forecast"
    assert result.rate_percent_per_hour == pytest.approx(2.0, abs=0.01)
    assert result.eta_hours == pytest.approx(15.0, abs=0.1)
    assert result.r_squared == pytest.approx(1.0, abs=0.01)
    assert result.eta_at is not None


def test_container_already_above_threshold_is_due_now(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        _add_measurements(db, PROTOTYPE, [(4, 80.0), (2, 84.0), (0, 88.0)])
        result = forecast_container(db, profile, _prototype(db))

    assert result.status == "due_now"
    assert result.eta_hours == 0.0


def test_bin_that_is_not_filling_has_no_arrival_time(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        _add_measurements(db, PROTOTYPE, [(6, 40.0), (4, 38.0), (2, 36.0), (0, 34.0)])
        result = forecast_container(db, profile, _prototype(db))

    # Отрицательный наклон не должен превращаться в огромный, но правдоподобный
    # срок: честнее сказать «прогноз недоступен».
    assert result.status == "unavailable"
    assert result.reason == "not_filling"
    assert result.eta_hours is None


def test_forecast_ignores_readings_from_before_the_last_collection(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        # Полный бак, вывоз, затем новый цикл наполнения.
        _add_measurements(db, PROTOTYPE, [(12, 70.0), (11, 78.0), (10, 86.0)])
        db.add(
            CollectionEvent(
                device_id=PROTOTYPE,
                collected_at=utcnow() - timedelta(hours=9),
                fill_ema_before_percent=86.0,
                fill_raw_before_percent=88.0,
                source="DISPATCHER",
            )
        )
        db.commit()
        _add_measurements(db, PROTOTYPE, [(6, 12.0), (4, 16.0), (2, 20.0), (0, 24.0)])

        result = forecast_container(db, profile, _prototype(db))

    # Если бы замеры до вывоза попали в выборку, наклон стал бы отрицательным.
    assert result.status == "forecast"
    assert result.samples == 4
    assert result.fill_percent == pytest.approx(24.0)
    assert result.rate_percent_per_hour == pytest.approx(2.0, abs=0.01)


def test_forecast_without_measurements_says_so(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        db.execute(delete(Telemetry).where(Telemetry.device_id == PROTOTYPE))
        db.commit()
        result = forecast_container(db, profile, _prototype(db))

    assert result.status == "unavailable"
    assert result.reason == "not_enough_measurements"


def test_forecast_endpoint_sorts_most_urgent_first(api) -> None:
    client, _, _ = api

    response = client.get("/api/eco/forecast")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 10

    etas = [row["eta_hours"] for row in payload if row["eta_hours"] is not None]
    assert etas == sorted(etas)


# --- Geometry and routing --------------------------------------------------


def test_haversine_matches_a_known_distance() -> None:
    kokshetau = Point("Кокшетау", 53.2833, 69.3833)
    astana = Point("Астана", 51.1694, 71.4491)

    # По прямой между городами около 274 км; по дороге примерно 300 км —
    # разницу и закрывает поправочный коэффициент извилистости в маршруте.
    assert haversine_km(kokshetau, astana) == pytest.approx(274, abs=5)


def test_distance_between_identical_points_is_zero() -> None:
    point = Point("Площадка", 53.28, 69.39)
    assert haversine_km(point, point) == pytest.approx(0.0)


def test_two_opt_untangles_a_crossing_route() -> None:
    # Квадрат, обойдённый крест-накрест: 0 → 2 → 1 → 3.
    depot = Point("База", 0.0, 0.0)
    crossing = [
        depot,
        Point("B", 0.1, 0.1),
        Point("A", 0.1, 0.0),
        Point("C", 0.0, 0.1),
    ]
    improved = two_opt(crossing)

    assert tour_length_km(improved) < tour_length_km(crossing)
    assert improved[0] is depot
    assert {point.label for point in improved} == {"База", "A", "B", "C"}


def test_nearest_neighbour_starts_at_the_depot_and_visits_everything() -> None:
    depot = Point("База", 53.26, 69.43)
    stops = [
        Point("Дальняя", 53.30, 69.41),
        Point("Ближняя", 53.265, 69.432),
        Point("Средняя", 53.28, 69.42),
    ]
    order = nearest_neighbour(depot, stops)

    assert order[0] is depot
    assert order[1].label == "Ближняя"
    assert len(order) == 4


def test_route_plan_prices_the_skipped_sites(api) -> None:
    client, _, _ = api

    response = client.get(
        "/api/eco/route", params={"horizon_hours": 24}, headers=DISPATCHER_HEADERS
    )
    assert response.status_code == 200
    plan = response.json()

    assert plan["baseline"]["stops"] == 10
    assert plan["planned"]["stops"] <= plan["baseline"]["stops"]
    assert plan["planned"]["distance_km"] <= plan["baseline"]["distance_km"]
    assert plan["distance_saved_km"] == pytest.approx(
        plan["baseline"]["distance_km"] - plan["planned"]["distance_km"], abs=0.01
    )
    assert plan["kzt_saved"] >= 0
    assert len(plan["skipped"]) == 10 - plan["planned"]["stops"]
    # Маршрут замкнутый: последний отрезок возвращает машину на базу.
    if plan["legs"]:
        assert plan["legs"][-1]["to_label"] == "Автобаза"


def test_longer_horizon_never_shrinks_the_route(api) -> None:
    client, _, _ = api

    short = client.get(
        "/api/eco/route", params={"horizon_hours": 6}, headers=DISPATCHER_HEADERS
    ).json()
    long = client.get(
        "/api/eco/route", params={"horizon_hours": 72}, headers=DISPATCHER_HEADERS
    ).json()

    assert long["planned"]["stops"] >= short["planned"]["stops"]


def test_route_requires_the_dispatcher_key(api) -> None:
    client, _, _ = api
    assert client.get("/api/eco/route").status_code == 401


# --- Bakery leftovers ------------------------------------------------------


def test_leftovers_forecast_uses_the_same_weekday(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        db.execute(delete(WriteOffRecord))
        db.commit()

        target = date(2026, 8, 18)  # вторник
        # Вторники стабильно тяжёлые, остальные дни — вдвое легче.
        for weeks_back in range(1, 5):
            db.add(
                WriteOffRecord(
                    profile_id=profile.id,
                    occurred_on=target - timedelta(weeks=weeks_back),
                    product="Багет",
                    kg_written_off=10.0,
                    kg_donated=8.0,
                    cost_kzt_per_kg=500.0,
                )
            )
            db.add(
                WriteOffRecord(
                    profile_id=profile.id,
                    occurred_on=target - timedelta(weeks=weeks_back, days=1),
                    product="Багет",
                    kg_written_off=5.0,
                    kg_donated=4.0,
                    cost_kzt_per_kg=500.0,
                )
            )
        db.commit()

        result = forecast_write_offs(db, profile, target=target, weeks=5)

    assert result.target_weekday == "Вторник"
    baguette = next(item for item in result.products if item.product == "Багет")
    assert baguette.basis == "same_weekday"
    assert baguette.expected_kg == pytest.approx(10.0)
    # Среднее по всем дням 7.5 кг, вторник тяжелее на треть.
    assert baguette.average_kg == pytest.approx(7.5)
    assert baguette.deviation_percent == pytest.approx(33.3, abs=0.1)


def test_leftovers_forecast_falls_back_when_weekday_has_no_history(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        db.execute(delete(WriteOffRecord))
        db.commit()

        target = date(2026, 8, 18)
        for days_back in (1, 2, 3):
            db.add(
                WriteOffRecord(
                    profile_id=profile.id,
                    occurred_on=target - timedelta(days=days_back),
                    product="Булочки",
                    kg_written_off=6.0,
                    kg_donated=5.0,
                    cost_kzt_per_kg=600.0,
                )
            )
        db.commit()

        result = forecast_write_offs(db, profile, target=target, weeks=1)

    buns = next(item for item in result.products if item.product == "Булочки")
    assert buns.basis == "all_days"
    assert buns.expected_kg == pytest.approx(6.0)


def test_rescued_value_uses_each_products_own_cost(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        db.execute(delete(WriteOffRecord))
        db.commit()

        target = date(2026, 8, 18)
        db.add(
            WriteOffRecord(
                profile_id=profile.id,
                occurred_on=target - timedelta(days=1),
                product="Хлеб",
                kg_written_off=10.0,
                kg_donated=10.0,
                cost_kzt_per_kg=450.0,
            )
        )
        db.add(
            WriteOffRecord(
                profile_id=profile.id,
                occurred_on=target - timedelta(days=1),
                product="Багет",
                kg_written_off=5.0,
                kg_donated=5.0,
                cost_kzt_per_kg=600.0,
            )
        )
        db.commit()

        result = forecast_write_offs(db, profile, target=target, weeks=2)

    # 10 * 450 + 5 * 600 = 7500, а не 15 кг по единой цене.
    assert result.rescued_value_kzt == pytest.approx(7500.0)
    assert result.total_donated_kg == pytest.approx(15.0)
    assert result.donation_rate_percent == pytest.approx(100.0)


def test_business_forecast_endpoint_defaults_to_tomorrow(api) -> None:
    client, _, _ = api

    response = client.get("/api/eco/business/forecast", headers=DISPATCHER_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    tomorrow = utcnow().date() + timedelta(days=1)
    assert payload["target_date"] == tomorrow.isoformat()
    assert payload["products"]
    assert payload["history_days"] > 0
