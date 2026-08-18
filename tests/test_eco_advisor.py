"""Recommendations must stay inside the numbers the engines computed."""

from __future__ import annotations

import json

from app.config import settings
from app.schemas import EcoRecommendation
from app.services.eco_advisor import (
    authorised_numbers,
    drop_ungrounded,
    uses_only_authorised_numbers,
)
from app.services.gemini_bot import gemini_bot


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}

FACTS = {
    "period_days": 30,
    "money": {"saved_kzt": 18196.4, "payback_months": None},
    "trips": {"saved": 55.0, "reduction_percent": 36.67},
    "bakery": {"target_date": "2026-08-18", "products": [{"expected_kg": 9.2}]},
}


def recommendation(detail: str) -> EcoRecommendation:
    return EcoRecommendation(title="Рекомендация", detail=detail)


def test_authorised_numbers_include_every_figure_that_was_supplied() -> None:
    numbers = authorised_numbers(FACTS)
    assert {30.0, 18196.4, 55.0, 36.67, 9.2} <= numbers
    # Dates are handed over as text, and their parts are quotable too.
    assert {2026.0, 8.0, 18.0} <= numbers


def test_a_number_that_was_never_supplied_is_refused() -> None:
    assert not uses_only_authorised_numbers(
        "Сэкономлено 999999 ₸", authorised_numbers(FACTS)
    )


def test_rounding_a_supplied_number_is_allowed() -> None:
    """Presenting 36.67% as 37% is formatting, not invention."""

    numbers = authorised_numbers(FACTS)
    assert uses_only_authorised_numbers("Сокращение рейсов на 37%", numbers)
    assert uses_only_authorised_numbers("Сэкономлено 18196.4 ₸", numbers)


def test_text_without_numbers_is_always_grounded() -> None:
    assert uses_only_authorised_numbers("Проверьте площадки утром", set())


def test_only_the_ungrounded_recommendation_is_dropped() -> None:
    kept = recommendation("За 30 дней сэкономлено 18196.4 ₸.")
    invented = recommendation("Дополнительно сэкономлено 7777 ₸.")

    survivors = drop_ungrounded([kept, invented], FACTS)

    assert [item.detail for item in survivors] == [kept.detail]


def test_recommendations_require_the_dispatcher_key(api) -> None:
    client, _, _ = api
    assert client.get("/api/eco/recommendations").status_code == 401


def test_recommendations_fall_back_to_local_rules_without_gemini(api) -> None:
    """The demo must produce advice with no key, no quota and no network."""

    client, _, _ = api
    response = client.get("/api/eco/recommendations", headers=DISPATCHER_HEADERS)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "offline-fallback"
    assert body["model"] is None
    assert body["recommendations"], "the dispatcher must still get advice"
    # The rules quote the same computed numbers the model would have received.
    assert drop_ungrounded(
        [EcoRecommendation.model_validate(item) for item in body["recommendations"]],
        body["facts"],
    ) == [EcoRecommendation.model_validate(item) for item in body["recommendations"]]


def test_recommendations_expose_the_facts_they_were_allowed_to_use(api) -> None:
    client, _, _ = api
    facts = client.get(
        "/api/eco/recommendations", headers=DISPATCHER_HEADERS
    ).json()["facts"]

    assert facts["containers"] > 0
    assert facts["period_days"] == 30
    assert "saved_kzt" in facts["money"]
    assert "km_planned" in facts["route_next_hours"]


def test_a_grounded_answer_from_the_model_is_returned(api, monkeypatch) -> None:
    client, _, _ = api

    async def interpret(facts):
        saved = facts["money"]["saved_kzt"]
        return (
            json.dumps(
                {
                    "recommendations": [
                        {
                            "title": "Экономия подтверждена",
                            "detail": f"За период сэкономлено {saved} ₸.",
                        }
                    ]
                }
            ),
            "gemini-test",
        )

    monkeypatch.setattr(gemini_bot, "interpret_metrics", interpret)
    body = client.get(
        "/api/eco/recommendations", headers=DISPATCHER_HEADERS
    ).json()

    assert body["provider"] == "google-gemini"
    assert body["model"] == "gemini-test"
    assert body["recommendations"][0]["title"] == "Экономия подтверждена"


def test_a_markdown_fenced_answer_is_still_read(api, monkeypatch) -> None:
    client, _, _ = api

    async def interpret(facts):
        payload = json.dumps(
            {"recommendations": [{"title": "Вывоз", "detail": "Проверьте площадки."}]}
        )
        return (f"```json\n{payload}\n```", "gemini-test")

    monkeypatch.setattr(gemini_bot, "interpret_metrics", interpret)
    body = client.get(
        "/api/eco/recommendations", headers=DISPATCHER_HEADERS
    ).json()

    assert body["provider"] == "google-gemini"
    assert body["recommendations"][0]["title"] == "Вывоз"


def test_an_invented_figure_never_reaches_the_dispatcher(api, monkeypatch) -> None:
    """The whole point of the grounded mode, proven end to end."""

    client, _, _ = api

    async def interpret(_facts):
        return (
            json.dumps(
                {
                    "recommendations": [
                        {
                            "title": "Экономия",
                            "detail": "За месяц сэкономлено 4200000 ₸.",
                        }
                    ]
                }
            ),
            "gemini-test",
        )

    monkeypatch.setattr(gemini_bot, "interpret_metrics", interpret)
    body = client.get(
        "/api/eco/recommendations", headers=DISPATCHER_HEADERS
    ).json()

    # Nothing survived the check, so the deterministic rules answer instead.
    assert body["provider"] == "offline-fallback"
    assert all(
        "4200000" not in item["detail"] for item in body["recommendations"]
    )


def test_an_unreadable_answer_degrades_instead_of_failing(api, monkeypatch) -> None:
    client, _, _ = api

    async def interpret(_facts):
        return ("извините, не смог разобрать данные", "gemini-test")

    monkeypatch.setattr(gemini_bot, "interpret_metrics", interpret)
    response = client.get("/api/eco/recommendations", headers=DISPATCHER_HEADERS)

    assert response.status_code == 200
    assert response.json()["provider"] == "offline-fallback"
