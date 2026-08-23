"""Площадка без DS18B20 продолжает жить как источник уровня заполнения.

Прошивка раньше выбрасывала весь замер, если датчик температуры не отвечал:
на экране такая площадка выглядела мёртвой целиком, хотя эхолот работал.
Проверки ниже закрепляют разделение — уровень принимается, пожарная
блокировка молчит, а заглушка в столбце температуры не выдаётся за показание.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import Alert, Telemetry


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}
DEVICE_ID = "municipal-prototype-001"


def _ingest(client, **overrides: object):
    payload: dict[str, object] = {
        "device_id": DEVICE_ID,
        "distance": 16.0,
        "temp_in": None,
        "temp_out": 25.0,
    }
    payload.update(overrides)
    return client.post("/api/sensors/ingest", json=payload)


def test_level_is_accepted_without_a_temperature_sensor(api) -> None:
    client, _, _ = api

    body = _ingest(client).json()

    # 16 см — ровно середина между пустым баком на 25 см и полным на 7 см.
    assert body["fill_percent"] == pytest.approx(50.0)
    assert body["temp_sensor_ok"] is False
    assert body["fire_risk"] is False


def test_missing_sensor_never_triggers_the_fire_interlock(api) -> None:
    """Молчание датчика — не доказательство, что в баке холодно.

    Но и закрывать заслонку не по чему: решение принимается только по
    настоящему измерению, иначе площадка без датчика блокировалась бы
    навсегда.
    """

    client, session_factory, _ = api

    for _ in range(3):
        assert _ingest(client).json()["action_triggered"] is None

    with session_factory() as db:
        assert db.scalars(select(Alert).where(Alert.alert_type == "FIRE_RISK")).all() == []


def test_stub_temperature_is_not_shown_as_a_reading(api) -> None:
    """В базе число есть, на экране его быть не должно.

    В temp_in_c ложится опорное значение — оно нужно арифметике дельты. Если
    отдать его наружу, диспетчер прочитает ровные 25 °C как «в баке спокойно»,
    хотя внутри никто ничего не мерил.
    """

    client, session_factory, _ = api

    _ingest(client)

    with session_factory() as db:
        stored = db.scalars(
            select(Telemetry)
            .where(Telemetry.device_id == DEVICE_ID)
            .order_by(Telemetry.id.desc())
        ).first()
        assert stored is not None
        assert stored.temp_sensor_ok is False
        assert stored.temperature_delta_c == pytest.approx(0.0)

    status = next(
        row
        for row in client.get(
            "/api/dispatcher/devices/status", headers=DISPATCHER_HEADERS
        ).json()
        if row["device_id"] == DEVICE_ID
    )
    assert status["temperature_in_c"] is None
    assert status["temperature_delta_c"] is None
    # Замер всё же был: экран отличает «нет связи» от «нет датчика» именно
    # по этому полю.
    assert status["measured_at"] is not None


def test_reconnected_sensor_starts_protecting_again(api) -> None:
    """Возврат датчика не требует перезапуска: первый же горячий замер закроет.

    Проверка идёт после замеров без температуры — иначе можно было бы не
    заметить, что предыдущая строка с заглушкой считается «уже горячей» или,
    наоборот, ломает определение начала эпизода.
    """

    client, _, _ = api

    _ingest(client)
    body = _ingest(client, temp_in=55.0).json()

    assert body["temp_sensor_ok"] is True
    assert body["fire_risk"] is True
    assert body["action_triggered"] == "CLOSE_LID"
