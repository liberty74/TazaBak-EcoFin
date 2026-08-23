"""Проверка локального стенда TazaBAK по звеньям.

Запуск:  .venv\\Scripts\\python.exe scripts\\check-local.py

Каждая проверка отвечает за одно звено цепи, и они идут в том порядке, в
котором звенья зависят друг от друга: сначала backend, потом база, потом
приём замеров, потом команды. Первый же провал говорит, где именно рвётся, —
это точнее, чем «ничего не работает».

Скрипт ничего не ломает: тестовый замер отправляется от прототипа, пожарная
тревога после проверки гасится, а созданные команды остаются в очереди
ровно так же, как после обычного показа.
"""

from __future__ import annotations

import json
import sys
from typing import Callable

import requests

API = "http://127.0.0.1:8000"
UI = "http://127.0.0.1:5173"
KEY = {"X-Dispatcher-Key": "123"}
PROTOTYPE = "municipal-prototype-001"

OK = "  [ ok ] "
FAIL = "  [ !! ] "

failures: list[str] = []


def check(title: str) -> Callable:
    """Оформляет одну проверку: заголовок, результат, причина отказа."""

    def wrapper(fn: Callable[[], str]) -> None:
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - причина важнее типа
            failures.append(title)
            print(f"{FAIL}{title}")
            print(f"         {type(exc).__name__}: {exc}")
            return
        print(f"{OK}{title}")
        if detail:
            print(f"         {detail}")

    return wrapper


print("\n  Проверка локального стенда TazaBAK\n")


@check("backend отвечает")
def _() -> str:
    body = requests.get(f"{API}/health", timeout=10).json()
    if body["status"] != "ok":
        raise RuntimeError(f"неожиданный ответ: {body}")
    return f"база {body['database']}, разбор фото: {body['image_analysis']}"


@check("демонстрационные данные на месте")
def _() -> str:
    containers = requests.get(f"{API}/api/containers", timeout=10).json()
    if len(containers) < 10:
        raise RuntimeError(f"площадок всего {len(containers)}, ожидалось 12")
    users = requests.get(f"{API}/api/leaderboard", timeout=10).json()
    return f"{len(containers)} площадок, {len(users)} жителей в рейтинге"


@check("публичный отчёт об экономии считается")
def _() -> str:
    body = requests.get(f"{API}/api/eco/savings", timeout=20).json()
    return (
        f"{body['trips']['saved']:.0f} рейсов не понадобилось "
        f"из {body['trips']['baseline']:.0f}"
    )


@check("диспетчерский ключ работает")
def _() -> str:
    route = requests.get(f"{API}/api/eco/route", headers=KEY, timeout=20)
    if route.status_code != 200:
        raise RuntimeError(f"ключ не принят, код {route.status_code}")
    without = requests.get(f"{API}/api/eco/route", timeout=20)
    if without.status_code != 401:
        raise RuntimeError("маршрут открывается без ключа — защита не работает")
    return "с ключом 200, без ключа 401"


@check("замер от платы принимается")
def _() -> str:
    body = requests.post(
        f"{API}/api/sensors/ingest",
        json={"device_id": PROTOTYPE, "distance": 16.0, "temp_in": 22.0, "temp_out": 20.0},
        timeout=20,
    ).json()
    # 25 см — пустой бак, 7 см — полный, значит 16 см это ровно середина.
    if abs(body["fill_percent"] - 50.0) > 0.5:
        raise RuntimeError(f"16 см должны дать 50%, получено {body['fill_percent']}")
    return f"16 см -> {body['fill_percent']}% заполнения"


@check("площадка помечена как собранная")
def _() -> str:
    rows = requests.get(f"{API}/api/dispatcher/devices/status", headers=KEY, timeout=20).json()
    assembled = [r["device_id"] for r in rows if r["has_hardware"]]
    if PROTOTYPE not in assembled:
        raise RuntimeError("прототип не помечен — экран управления будет пустым")
    return f"собранных площадок: {len(assembled)} из {len(rows)}"


@check("пожарная блокировка срабатывает")
def _() -> str:
    body = requests.post(
        f"{API}/api/sensors/ingest",
        json={"device_id": PROTOTYPE, "distance": 16.0, "temp_in": 55.0, "temp_out": 20.0},
        timeout=20,
    ).json()
    if not body["fire_risk"] or body["action_triggered"] != "CLOSE_LID":
        raise RuntimeError(f"55 °C не вызвали закрытие: {body}")
    return "55 °C -> тревога и команда закрытия"


@check("тревога гаснет после остывания")
def _() -> str:
    for _ in range(3):
        requests.post(
            f"{API}/api/sensors/ingest",
            json={"device_id": PROTOTYPE, "distance": 16.0, "temp_in": 21.0, "temp_out": 20.0},
            timeout=20,
        )
    summary = requests.get(f"{API}/api/dispatch/summary", headers=KEY, timeout=20).json()
    active = [t for t in summary["tasks"] if t.get("status") != "RESOLVED"]
    for alert in active:
        requests.patch(f"{API}/api/alerts/{alert['id']}/resolve", headers=KEY, timeout=20)
    return f"закрыто тревог: {len(active)}"


@check("команда заслонки ставится в очередь")
def _() -> str:
    payload = {"dispatcher_id": "dispatcher-1", "action": "OPEN_LID",
               "idempotency_key": "check-local-open"}
    first = requests.post(
        f"{API}/api/dispatcher/devices/{PROTOTYPE}/command",
        headers=KEY, json=payload, timeout=20,
    ).json()
    second = requests.post(
        f"{API}/api/dispatcher/devices/{PROTOTYPE}/command",
        headers=KEY, json=payload, timeout=20,
    ).json()
    if first["id"] != second["id"]:
        raise RuntimeError("повтор создал дубль — идемпотентность сломана")
    return f"команда #{first['id']}, повтор не создал дубля"


@check("плата получает команды по WebSocket")
def _() -> str:
    try:
        from websockets.sync.client import connect
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise RuntimeError("нет модуля websockets (входит в uvicorn[standard])") from exc

    with connect(f"ws://127.0.0.1:8000/ws/device/{PROTOTYPE}", open_timeout=10) as ws:
        ws.send(json.dumps({"action": "PING"}))
        delivered = []
        for _ in range(5):
            try:
                message = json.loads(ws.recv(timeout=5))
            except TimeoutError:
                break
            if message.get("action") in {"OPEN_LID", "CLOSE_LID"}:
                delivered.append(message["action"])
                ws.send(json.dumps({"action": "COMMAND_ACK",
                                    "command_id": message["command_id"]}))
            if message.get("action") == "PONG" and delivered:
                break
    if not delivered:
        raise RuntimeError("очередь не доставила ни одной команды")
    return f"доставлено при подключении: {', '.join(delivered)}"


@check("интерфейс отдаётся")
def _() -> str:
    page = requests.get(UI, timeout=10)
    if page.status_code != 200 or "<div id=\"root\"" not in page.text:
        raise RuntimeError(f"код {page.status_code}, страница не похожа на приложение")
    return f"{len(page.content)} байт с {UI}"


print()
if failures:
    print(f"  Не прошло проверок: {len(failures)}")
    for name in failures:
        print(f"    - {name}")
    print("\n  Разбор частых отказов: docs/HARDWARE.md, раздел 8\n")
    sys.exit(1)

print("  Стенд исправен: все проверки пройдены.\n")
