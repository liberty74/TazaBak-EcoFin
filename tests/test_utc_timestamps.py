"""Время в ответах API помечено как UTC.

Даты в базе лежат наивными и означают UTC. Строка без пометки — «2026-08-23T15:07:19»
— по спецификации разбирается браузером как местное время, и замер, пришедший
секунду назад, показывался молчащим ровно на величину часового пояса. В
Казахстане это пять часов: плата выглядела мёртвой, а тревоги — случившимися
утром.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.config import settings


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}
DEVICE_ID = "municipal-prototype-001"


def _assert_utc(value: str, field: str) -> None:
    assert value is not None, f"{field} отсутствует"
    assert value.endswith("Z") or "+00:00" in value, (
        f"{field} = {value!r} — без пометки часового пояса; "
        "браузер прочитает это как местное время"
    )
    # Строка должна остаться разбираемой: пометка не должна ломать формат.
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_telemetry_response_marks_time_as_utc(api) -> None:
    client, _, _ = api

    body = client.post(
        "/api/sensors/ingest",
        json={"device_id": DEVICE_ID, "distance": 16.0, "temp_in": 22.0, "temp_out": 20.0},
    ).json()

    _assert_utc(body["received_at"], "received_at")


def test_device_status_marks_time_as_utc(api) -> None:
    """Именно по этому полю экран решает, на связи ли плата."""

    client, _, _ = api

    client.post(
        "/api/sensors/ingest",
        json={"device_id": DEVICE_ID, "distance": 16.0, "temp_in": 22.0, "temp_out": 20.0},
    )
    rows = client.get(
        "/api/dispatcher/devices/status", headers=DISPATCHER_HEADERS
    ).json()
    row = next(item for item in rows if item["device_id"] == DEVICE_ID)

    _assert_utc(row["measured_at"], "measured_at")
    _assert_utc(row["last_seen_at"], "last_seen_at")


def test_alert_time_marks_utc(api) -> None:
    client, _, _ = api

    client.post(
        "/api/sensors/ingest",
        json={"device_id": DEVICE_ID, "distance": 16.0, "temp_in": 55.0, "temp_out": 20.0},
    )
    summary = client.get("/api/dispatch/summary", headers=DISPATCHER_HEADERS).json()

    _assert_utc(summary["generated_at"], "generated_at")
    assert summary["tasks"], "тревога не создалась — проверять нечего"
    _assert_utc(summary["tasks"][0]["created_at"], "created_at тревоги")


@pytest.mark.parametrize(
    ("path", "field"),
    [
        ("/api/eco/savings", "generated_at"),
        ("/api/eco/revenue", "generated_at"),
    ],
)
def test_public_reports_mark_utc(api, path: str, field: str) -> None:
    client, _, _ = api

    _assert_utc(client.get(path).json()[field], f"{path} → {field}")


def test_incoming_time_with_offset_is_still_accepted(api) -> None:
    """Пометка на выходе не должна ломать приём.

    Плата присылает время со смещением, сервер приводит его к UTC. Проверка
    закрывает обратную дорогу: сериализация и разбор не должны разъехаться.
    """

    client, _, _ = api

    body = client.post(
        "/api/sensors/ingest",
        json={
            "device_id": DEVICE_ID,
            "distance": 16.0,
            "temp_in": 22.0,
            "temp_out": 20.0,
            "measured_at": "2026-08-23T20:07:19+05:00",
        },
    )

    assert body.status_code == 200
    _assert_utc(body.json()["received_at"], "received_at")
