"""EcoFin: savings arithmetic, collection detection and the economics API."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import delete, func, select

from app.config import settings
from app.models import (
    BinContainer,
    BioAnalysis,
    CollectionEvent,
    CostProfile,
    Device,
    SavingsSnapshot,
    WriteOffRecord,
    utcnow,
)
from app.services.eco_savings import (
    ProfileNotConfiguredError,
    build_savings_report,
    get_profile,
    stop_cost,
)


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}


def _clear_history(db) -> None:
    """Remove seeded history so a test fully controls the numbers."""

    db.execute(delete(CollectionEvent))
    db.execute(delete(BioAnalysis))
    db.execute(delete(WriteOffRecord))
    db.commit()


def _municipal_device_ids(db) -> list[str]:
    return list(
        db.scalars(
            select(BinContainer.device_id)
            .join(Device, Device.id == BinContainer.device_id)
            .where(BinContainer.is_active.is_(True), Device.kind == "municipal")
            .order_by(BinContainer.id.asc())
        ).all()
    )


def test_stop_cost_matches_the_documented_formula(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        profile.km_per_stop = 1.5
        profile.fuel_consumption_l_per_100km = 26.0
        profile.fuel_price_kzt_per_liter = 331.0
        profile.minutes_per_stop = 6.0
        profile.crew_cost_kzt_per_hour = 2_500.0
        db.commit()

        cost = stop_cost(profile)

    # 1.5 км / 100 * 26 л = 0.39 л; 0.39 * 331 ₸ = 129.09 ₸ топлива.
    assert cost.liters == pytest.approx(0.39)
    assert cost.fuel_kzt == pytest.approx(129.09)
    # 6 минут = 0.1 часа; 0.1 * 2500 ₸ = 250 ₸ бригады.
    assert cost.crew_kzt == pytest.approx(250.0)
    assert cost.total_kzt == pytest.approx(379.09)


def test_savings_report_multiplies_saved_stops_by_stop_cost(api) -> None:
    client, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)
        profile = get_profile(db)
        profile.km_per_stop = 1.5
        profile.fuel_consumption_l_per_100km = 26.0
        profile.fuel_price_kzt_per_liter = 331.0
        profile.minutes_per_stop = 6.0
        profile.crew_cost_kzt_per_hour = 2_500.0
        profile.baseline_trips_per_week = 7.0
        profile.co2_kg_per_liter = 2.68
        db.commit()

        device_ids = _municipal_device_ids(db)
        containers = len(device_ids)
        period_end = utcnow()
        period_start = period_end - timedelta(days=7)

        # One servicing per site over a week, against a daily schedule.
        for device_id in device_ids:
            db.add(
                CollectionEvent(
                    device_id=device_id,
                    collected_at=period_end - timedelta(days=3),
                    fill_ema_before_percent=90.0,
                    fill_raw_before_percent=92.0,
                    source="DISPATCHER",
                )
            )
        db.commit()

        report = build_savings_report(db, profile, period_start, period_end)

    baseline = 7.0 * containers
    saved = baseline - containers
    assert report.containers == containers
    assert report.trips.baseline == pytest.approx(baseline)
    assert report.trips.actual == containers
    assert report.trips.saved == pytest.approx(saved)
    assert report.trips.reduction_percent == pytest.approx(saved / baseline * 100, abs=0.01)
    assert report.trips.average_fill_at_collection_percent == pytest.approx(90.0)

    assert report.resources.km_saved == pytest.approx(saved * 1.5, abs=0.01)
    assert report.resources.liters_saved == pytest.approx(saved * 0.39, abs=0.01)
    assert report.resources.co2_kg_saved == pytest.approx(
        saved * 0.39 * 2.68, abs=0.01
    )
    assert report.money.fuel_kzt == pytest.approx(saved * 129.09, abs=0.01)
    assert report.money.crew_kzt == pytest.approx(saved * 250.0, abs=0.01)
    assert report.money.total_kzt == pytest.approx(saved * 379.09, abs=0.02)


def test_servicing_more_often_than_schedule_reports_zero_not_negative(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)
        profile = get_profile(db)
        profile.baseline_trips_per_week = 1.0
        db.commit()

        period_end = utcnow()
        period_start = period_end - timedelta(days=7)
        # Каждую площадку обслужили дважды за неделю при графике «раз в неделю».
        for device_id in _municipal_device_ids(db):
            for day in (1, 4):
                db.add(
                    CollectionEvent(
                        device_id=device_id,
                        collected_at=period_start + timedelta(days=day),
                        fill_ema_before_percent=30.0,
                        fill_raw_before_percent=30.0,
                        source="DISPATCHER",
                    )
                )
        db.commit()

        report = build_savings_report(db, profile, period_start, period_end)

    assert report.trips.saved == 0.0
    assert report.money.total_kzt == 0.0
    assert report.resources.co2_kg_saved == 0.0
    assert report.trips.reduction_percent == 0.0
    assert report.payback.payback_months is None


def test_empty_period_returns_zeros_without_dividing_by_zero(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)
        profile = get_profile(db)
        period_end = utcnow()
        report = build_savings_report(
            db, profile, period_end - timedelta(days=30), period_end
        )

    assert report.trips.actual == 0
    assert report.trips.average_fill_at_collection_percent is None
    assert report.bread.kg_total == 0.0
    assert report.bread.rescued_value_kzt == 0.0
    # No servicing at all means the whole schedule was avoided.
    assert report.trips.saved == pytest.approx(report.trips.baseline)


def test_report_rejects_inverted_period(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        now = utcnow()
        with pytest.raises(ValueError):
            build_savings_report(db, profile, now, now - timedelta(days=1))


def test_weekly_breakdown_covers_the_whole_period(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)
        profile = get_profile(db)
        period_end = utcnow()
        report = build_savings_report(
            db, profile, period_end - timedelta(days=30), period_end
        )

    # Thirty days is four full weeks plus a partial fifth bucket.
    assert len(report.weekly) == 5
    assert report.weekly[0].week_start == report.period_start.date()
    assert sum(point.trips_saved for point in report.weekly) == pytest.approx(
        report.trips.saved, abs=0.05
    )


def test_only_the_unfinished_week_is_marked_partial(api) -> None:
    """Неполная корзина набирает меньше просто потому, что ещё идёт.

    Без пометки график падал бы на ней в пол, и это читалось бы как обвал
    экономии вместо «неделя ещё не закончилась».
    """

    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        period_end = utcnow()
        ragged = build_savings_report(
            db, profile, period_end - timedelta(days=30), period_end
        )
        whole_weeks = build_savings_report(
            db, profile, period_end - timedelta(days=28), period_end
        )

    assert [point.is_partial for point in ragged.weekly] == [
        False,
        False,
        False,
        False,
        True,
    ]
    # Двадцать восемь дней делятся на недели без остатка — помечать нечего.
    assert not any(point.is_partial for point in whole_weeks.weekly)


def test_pilot_tariff_leaves_the_client_in_profit(api) -> None:
    """Подписка не может стоить дороже экономии, которую она создаёт.

    Тариф в сиде однажды был назначен без опоры на расчёт: 5 000 ₸ за бак
    при экономии около 2 460 ₸ на бак. Оператор уходил в минус, срок
    окупаемости не определялся, и это было видно на главном экране.
    Тест закрепляет правило, а не конкретную цену.
    """

    _, session_factory, _ = api

    with session_factory() as db:
        profile = get_profile(db)
        period_end = utcnow()
        report = build_savings_report(
            db, profile, period_end - timedelta(days=30), period_end
        )

    payback = report.payback
    assert payback.monthly_savings_kzt > payback.monthly_subscription_kzt, (
        "подписка съедает всю экономию — клиенту незачем покупать платформу"
    )
    assert payback.net_monthly_kzt > 0
    assert payback.payback_months is not None
    # Дольше пяти лет окупаемость перестаёт быть аргументом для акимата.
    assert payback.payback_months < 60


def test_payback_subtracts_subscription_before_dividing(api) -> None:
    _, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)
        profile = get_profile(db)
        profile.install_price_kzt = 50_000.0
        profile.subscription_kzt_per_month = 5_000.0
        db.commit()

        period_end = utcnow()
        report = build_savings_report(
            db, profile, period_end - timedelta(days=30), period_end
        )
        containers = report.containers

    expected_subscription = 5_000.0 * containers
    assert report.payback.monthly_subscription_kzt == pytest.approx(
        expected_subscription
    )
    assert report.payback.install_total_kzt == pytest.approx(50_000.0 * containers)
    assert report.payback.net_monthly_kzt == pytest.approx(
        report.payback.monthly_savings_kzt - expected_subscription, abs=0.01
    )
    if report.payback.net_monthly_kzt > 0:
        assert report.payback.payback_months == pytest.approx(
            report.payback.install_total_kzt / report.payback.net_monthly_kzt,
            abs=0.1,
        )
    else:
        assert report.payback.payback_months is None


def test_telemetry_detects_collection_from_a_sharp_level_drop(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"

    with session_factory() as db:
        _clear_history(db)

    # 9 см от крышки — бак почти полон, затем 24 см — бак опорожнён.
    full = client.post(
        "/api/sensors/ingest",
        json={"device_id": device_id, "distance": 9, "temp_in": 20, "temp_out": 18},
    )
    assert full.status_code == 200
    assert full.json()["fill_percent"] > settings.collection_drop_from_percent

    emptied = client.post(
        "/api/sensors/ingest",
        json={"device_id": device_id, "distance": 24, "temp_in": 20, "temp_out": 18},
    )
    assert emptied.status_code == 200

    with session_factory() as db:
        events = db.scalars(
            select(CollectionEvent).where(CollectionEvent.device_id == device_id)
        ).all()
        assert len(events) == 1
        event = events[0]
        assert event.source == "SENSOR"
        # Уровень записывается тот, который видел диспетчер до вывоза.
        assert event.fill_raw_before_percent > 80.0
        assert event.container_id is not None


def test_gradual_filling_is_not_mistaken_for_a_collection(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"

    with session_factory() as db:
        _clear_history(db)

    for distance in (24, 20, 16, 12, 9):
        response = client.post(
            "/api/sensors/ingest",
            json={
                "device_id": device_id,
                "distance": distance,
                "temp_in": 20,
                "temp_out": 18,
            },
        )
        assert response.status_code == 200

    with session_factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(CollectionEvent)
                .where(CollectionEvent.device_id == device_id)
            )
            == 0
        )


def test_savings_endpoint_is_public_and_exposes_its_own_formula(api) -> None:
    client, _, _ = api

    response = client.get("/api/eco/savings", params={"days": 30})
    assert response.status_code == 200
    payload = response.json()

    assert payload["city"] == "Кокшетау"
    assert payload["containers"] == 10
    formula = payload["formula"]
    # Каждое число на экране должно раскрываться в исходные параметры.
    assert formula["km_per_stop"] == 1.5
    assert formula["fuel_price_kzt_per_liter"] == 331.0
    assert formula["co2_kg_per_liter"] == 2.68
    assert payload["money"]["total_kzt"] == pytest.approx(
        payload["trips"]["saved"] * formula["kzt_per_saved_stop"], abs=0.05
    )


def test_savings_endpoint_validates_the_period(api) -> None:
    client, _, _ = api

    assert client.get("/api/eco/savings", params={"days": 0}).status_code == 422
    assert client.get("/api/eco/savings", params={"days": 400}).status_code == 422


def test_missing_cost_profile_returns_404_instead_of_guessing(api) -> None:
    client, session_factory, _ = api

    with session_factory() as db:
        db.execute(delete(CostProfile))
        db.commit()

    response = client.get("/api/eco/savings")
    assert response.status_code == 404
    assert response.json()["detail"] == "Экономический профиль не настроен"

    with session_factory() as db:
        with pytest.raises(ProfileNotConfiguredError):
            get_profile(db)


def test_profile_endpoints_require_the_dispatcher_key(api) -> None:
    client, _, _ = api

    assert client.get("/api/eco/profile").status_code == 401
    assert client.put("/api/eco/profile", json={"km_per_stop": 2.0}).status_code == 401
    assert client.get("/api/eco/collections").status_code == 401
    assert client.post("/api/eco/snapshots").status_code == 401


def test_dispatcher_retunes_fuel_price_and_report_follows(api) -> None:
    client, _, _ = api

    before = client.get("/api/eco/savings").json()["money"]["fuel_kzt"]

    updated = client.put(
        "/api/eco/profile",
        json={"fuel_price_kzt_per_liter": 662.0},
        headers=DISPATCHER_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["fuel_price_kzt_per_liter"] == 662.0
    # Остальные параметры не должны измениться от частичного обновления.
    assert updated.json()["km_per_stop"] == 1.5

    after = client.get("/api/eco/savings").json()["money"]["fuel_kzt"]
    assert after == pytest.approx(before * 2, abs=0.05)


def test_profile_update_rejects_impossible_values(api) -> None:
    client, _, _ = api

    assert (
        client.put(
            "/api/eco/profile",
            json={"km_per_stop": -1},
            headers=DISPATCHER_HEADERS,
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/eco/profile",
            json={"unknown_field": 1},
            headers=DISPATCHER_HEADERS,
        ).status_code
        == 422
    )


def test_manual_collection_is_recorded_once_per_idempotency_key(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"

    payload = {"device_id": device_id, "idempotency_key": "manual-run-0001"}
    first = client.post("/api/eco/collections", json=payload, headers=DISPATCHER_HEADERS)
    assert first.status_code == 201
    assert first.json()["source"] == "DISPATCHER"

    replay = client.post("/api/eco/collections", json=payload, headers=DISPATCHER_HEADERS)
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]

    with session_factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(CollectionEvent)
                .where(CollectionEvent.idempotency_key == "manual-run-0001")
            )
            == 1
        )


def test_snapshot_freezes_the_numbers_that_were_reported(api) -> None:
    client, session_factory, _ = api

    report = client.get("/api/eco/savings", params={"days": 30}).json()
    created = client.post(
        "/api/eco/snapshots", params={"days": 30}, headers=DISPATCHER_HEADERS
    )
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["kzt_saved"] == pytest.approx(report["money"]["total_kzt"], abs=1.0)
    assert snapshot["containers"] == report["containers"]

    listed = client.get("/api/eco/snapshots", headers=DISPATCHER_HEADERS)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [snapshot["id"]]

    with session_factory() as db:
        stored = db.scalar(select(SavingsSnapshot))
        assert stored is not None
        # Полный отчёт сохраняется целиком, вместе с формулой.
        assert stored.payload["formula"]["km_per_stop"] == 1.5


def test_write_off_day_is_corrected_not_duplicated(api) -> None:
    client, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)

    body = {
        "occurred_on": "2026-08-16",
        "product": "Хлеб пшеничный",
        "kg_written_off": 12.0,
        "kg_donated": 9.0,
        "cost_kzt_per_kg": 450.0,
    }
    first = client.put("/api/eco/write-offs", json=body, headers=DISPATCHER_HEADERS)
    assert first.status_code == 200
    assert first.json()["kg_donated"] == 9.0

    corrected = client.put(
        "/api/eco/write-offs",
        json={**body, "kg_donated": 11.0},
        headers=DISPATCHER_HEADERS,
    )
    assert corrected.status_code == 200
    assert corrected.json()["id"] == first.json()["id"]
    assert corrected.json()["kg_donated"] == 11.0

    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(WriteOffRecord)) == 1


def test_write_off_cannot_donate_more_than_was_written_off(api) -> None:
    client, _, _ = api

    response = client.put(
        "/api/eco/write-offs",
        json={
            "occurred_on": "2026-08-16",
            "product": "Багет",
            "kg_written_off": 4.0,
            "kg_donated": 9.0,
            "cost_kzt_per_kg": 450.0,
        },
        headers=DISPATCHER_HEADERS,
    )
    assert response.status_code == 422


def test_donated_bread_reaches_the_savings_report(api) -> None:
    client, session_factory, _ = api

    with session_factory() as db:
        _clear_history(db)

    today = utcnow().date().isoformat()
    client.put(
        "/api/eco/write-offs",
        json={
            "occurred_on": today,
            "product": "Хлеб пшеничный",
            "kg_written_off": 20.0,
            "kg_donated": 15.0,
            "cost_kzt_per_kg": 450.0,
        },
        headers=DISPATCHER_HEADERS,
    )

    bread = client.get("/api/eco/savings", params={"days": 7}).json()["bread"]
    assert bread["kg_from_business"] == pytest.approx(15.0)
    assert bread["kg_total"] == pytest.approx(
        bread["kg_from_citizens"] + 15.0
    )
    # 450 ₸ за килограмм — себестоимость из самой записи о списании.
    # Это стоимость спасённого продукта, а не деньги, вернувшиеся пекарне,
    # поэтому она и не входит в money.total_kzt.
    assert bread["rescued_value_kzt"] == pytest.approx(15.0 * 450.0, abs=0.01)
    savings = client.get("/api/eco/savings", params={"days": 7}).json()
    assert savings["money"]["total_kzt"] != bread["rescued_value_kzt"]
