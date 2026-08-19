"""EcoFin: the revenue model and the honesty rules it has to keep."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.config import settings
from app.models import utcnow
from app.services.eco_revenue import _plural, build_revenue_model
from app.services.eco_savings import build_savings_report, get_profile


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}


def _model(session_factory, projection_containers: int | None = None):
    with session_factory() as db:
        profile = get_profile(db)
        period_end = utcnow()
        period_start = period_end - timedelta(days=30)
        report = build_savings_report(db, profile, period_start, period_end)
        return build_revenue_model(
            db,
            profile,
            report,
            period_start,
            period_end,
            projection_containers=projection_containers,
        )


def test_every_stream_carries_the_arithmetic_that_produced_it(api) -> None:
    """Число без основания на защите не защищаемо."""

    _, session_factory, _ = api
    model = _model(session_factory)

    assert model.pilot.streams, "модель доходов не должна быть пустой"
    for stream in model.pilot.streams:
        assert stream.basis.strip(), f"поток {stream.key} без основания"
        assert "×" in stream.basis, f"поток {stream.key} не показывает умножение"
        assert stream.note.strip(), f"поток {stream.key} без пояснения"


def test_one_time_hardware_margin_stays_out_of_recurring_revenue(api) -> None:
    """Разовую маржу нельзя складывать с подпиской: так выручка удваивается."""

    _, session_factory, _ = api
    model = _model(session_factory)

    hardware = next(s for s in model.pilot.streams if s.key == "hardware_margin")
    assert not hardware.is_recurring
    assert hardware.monthly_kzt > 0

    recurring = sum(s.monthly_kzt for s in model.pilot.streams if s.is_recurring)
    assert model.pilot.monthly_recurring_kzt == pytest.approx(recurring, abs=0.01)
    assert model.pilot.one_time_kzt == pytest.approx(hardware.monthly_kzt, abs=0.01)
    # Главная проверка: маржа не просочилась в регулярную выручку.
    assert model.pilot.monthly_recurring_kzt < hardware.monthly_kzt + recurring


def test_annual_revenue_is_twelve_recurring_months(api) -> None:
    _, session_factory, _ = api
    model = _model(session_factory)

    assert model.pilot.annual_recurring_kzt == pytest.approx(
        model.pilot.monthly_recurring_kzt * 12.0, abs=0.01
    )


def test_projection_is_absent_until_it_is_asked_for(api) -> None:
    """Проекция не должна появляться сама — её легко принять за факт."""

    _, session_factory, _ = api
    assert _model(session_factory).projection is None


def test_projection_scales_the_pilot_and_stays_labelled(api) -> None:
    _, session_factory, _ = api
    model = _model(session_factory, projection_containers=1_200)

    assert model.projection is not None
    assert model.projection.containers == 1_200
    assert model.projection.title != model.pilot.title
    assert (
        model.projection.monthly_recurring_kzt > model.pilot.monthly_recurring_kzt
    )

    pilot_saas = next(s for s in model.pilot.streams if s.key == "operator_saas")
    scaled_saas = next(s for s in model.projection.streams if s.key == "operator_saas")
    factor = 1_200 / model.pilot.containers
    assert scaled_saas.monthly_kzt == pytest.approx(
        pilot_saas.monthly_kzt * factor, rel=0.01
    )


def test_assumptions_are_stated_next_to_the_numbers(api) -> None:
    """Проекция без перечисленных допущений — это обещание, а не расчёт."""

    _, session_factory, _ = api
    model = _model(session_factory, projection_containers=500)

    assert len(model.assumptions) >= 3
    assert any("допущение" in text.lower() for text in model.assumptions)


def test_business_tariff_names_the_loss_it_has_to_beat(api) -> None:
    """Тариф кабинета оправдан только предотвращённым убытком."""

    _, session_factory, _ = api
    model = _model(session_factory)

    business = next(s for s in model.pilot.streams if s.key == "business_saas")
    assert "%" in business.note, "не указан порог окупаемости для пекарни"


def test_revenue_endpoint_is_public_and_matches_the_service(api) -> None:
    """Бизнес-модель — аргумент, а не секрет, поэтому отчёт открыт."""

    client, session_factory, _ = api

    response = client.get("/api/eco/revenue", params={"days": 30})
    assert response.status_code == 200
    payload = response.json()

    assert payload["currency"] == "KZT"
    assert payload["projection"] is None
    assert payload["pilot"]["monthly_recurring_kzt"] == pytest.approx(
        _model(session_factory).pilot.monthly_recurring_kzt, abs=0.01
    )


def test_revenue_endpoint_projects_on_request(api) -> None:
    client, _, _ = api

    response = client.get(
        "/api/eco/revenue", params={"days": 30, "projection_containers": 800}
    )
    assert response.status_code == 200
    projection = response.json()["projection"]
    assert projection is not None
    assert projection["containers"] == 800


def test_revenue_endpoint_rejects_a_nonsense_scale(api) -> None:
    client, _, _ = api

    assert (
        client.get(
            "/api/eco/revenue", params={"projection_containers": 0}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, "бак"),
        (2, "бака"),
        (4, "бака"),
        (5, "баков"),
        (11, "баков"),
        (14, "баков"),
        (21, "бак"),
        (102, "бака"),
        (111, "баков"),
    ],
)
def test_russian_plurals_follow_the_language_not_the_loop(
    count: int, expected: str
) -> None:
    """Подпись «1 баков» сразу выдаёт, что текст собран машиной."""

    assert _plural(count, "бак", "бака", "баков") == expected
