from __future__ import annotations

import asyncio
from io import BytesIO
import threading
from types import SimpleNamespace
import xml.etree.ElementTree as ElementTree

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.config import settings
from app.models import (
    Alert,
    BinContainer,
    BioAnalysis,
    Device,
    DeviceCommand,
    EcoNFT,
    ForumMessage,
    PointTransaction,
    ShopItem,
    ShopPurchase,
    Telemetry,
    User,
    UserTask,
    VisionFrame,
    VolunteerTask,
)
from app.services.seed import seed_initial_data
from app.services.gemini_bot import GeminiBot, GeminiUserContext
import app.services.websocket as websocket_service
from app.services.yolo import DetectedObject


DISPATCHER_HEADERS = {"X-Dispatcher-Key": settings.dispatcher_api_key}


def make_png(
    size: tuple[int, int] = (1, 1),
    color: tuple[int, int, int] = (30, 160, 80),
) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


PNG_1X1 = make_png()
PNG_1X1_ALT = make_png(color=(190, 80, 40))


def telemetry_payload(
    device_id: str,
    distance: float,
    temp_in: float = 20.0,
    temp_out: float = 20.0,
) -> dict[str, str | float]:
    return {
        "device_id": device_id,
        "distance": distance,
        "temp_in": temp_in,
        "temp_out": temp_out,
    }


def detected(label: str, confidence: float = 0.95) -> DetectedObject:
    return DetectedObject(
        label=label,
        confidence=confidence,
        bounding_box=[1.0, 2.0, 30.0, 40.0],
    )


def post_bio(
    client,
    *,
    device_id: str = "bio-central-park-001",
    data: bytes = PNG_1X1,
    idempotency_key: str = "bio-test-operation-001",
):
    return client.post(
        "/api/bio/analyze",
        data={
            "device_id": device_id,
            "user_id": "123",
            "idempotency_key": idempotency_key,
        },
        files={"file": ("bread.png", data, "image/png")},
    )


def test_health_openapi_and_websocket_routes(api) -> None:
    client, _, _ = api
    assert client.get("/health").json() == {
        "status": "ok",
        "database": "reachable",
    }

    paths = set(client.get("/openapi.json").json()["paths"])
    required_paths = {
        "/api/sensors/ingest",
        "/api/vision/frame",
        "/api/bio/analyze",
        "/api/dispatch/summary",
        "/api/dispatch/briefing",
        "/api/alerts/{alert_id}/resolve",
        "/api/dispatcher/devices/{device_id}/command",
        "/api/dispatcher/commands",
        "/api/users/{user_id}",
        "/api/users/{user_id}/transactions",
        "/api/users/{user_id}/nfts",
        "/api/users/{user_id}/dashboard",
        "/api/leaderboard",
        "/api/containers",
        "/api/volunteer/tasks",
        "/api/volunteer/tasks/{task_id}/register",
        "/api/volunteer/tasks/{task_id}/complete",
        "/api/shop/items",
        "/api/shop/buy",
        "/api/shop/mint-nft",
        "/api/community/chat",
        "/api/ai/chat",
    }
    assert required_paths <= paths
    with client.websocket_connect("/ws/device/route-smoke") as websocket:
        websocket.send_json({"action": "PING"})
        assert websocket.receive_json() == {"action": "PONG"}


def test_seed_roles_opening_ledger_and_idempotence(api) -> None:
    client, session_factory, _ = api

    profile = client.get("/api/users/123")
    assert profile.status_code == 200
    assert profile.json() == {
        "id": 1,
        "username": "123",
        "role": "user",
        "points": 120,
        "status_tier": "Eco-Hero",
    }

    with session_factory() as db:
        roles = dict(db.execute(select(User.username, User.role)).all())
        before = {
            "users": db.scalar(select(func.count()).select_from(User)),
            "containers": db.scalar(select(func.count()).select_from(BinContainer)),
            "tasks": db.scalar(select(func.count()).select_from(VolunteerTask)),
            "items": db.scalar(select(func.count()).select_from(ShopItem)),
            "messages": db.scalar(select(func.count()).select_from(ForumMessage)),
            "opening_ledger": db.scalar(
                select(func.count())
                .select_from(PointTransaction)
                .where(PointTransaction.transaction_type == "OPENING_BALANCE")
            ),
        }
        user = db.scalar(select(User).where(User.username == "123"))
        container = db.scalar(
            select(BinContainer).where(
                BinContainer.device_id == "municipal-prototype-001"
            )
        )
        assert user is not None and container is not None
        user.points = 77
        container.last_fill_level = 42.5
        db.commit()

    assert roles["123"] == "user"
    assert roles["volunteer-1"] == "volunteer"
    assert roles["dispatcher-1"] == "dispatcher"
    assert before == {
        "users": 6,
            "containers": 3,
            "tasks": 33,
        "items": 3,
        "messages": 2,
        "opening_ledger": 5,
    }
    assert all(row["role"] != "dispatcher" for row in client.get("/api/leaderboard").json())

    seed_initial_data(session_factory)
    seed_initial_data(session_factory)
    with session_factory() as db:
        after = {
            "users": db.scalar(select(func.count()).select_from(User)),
            "containers": db.scalar(select(func.count()).select_from(BinContainer)),
            "tasks": db.scalar(select(func.count()).select_from(VolunteerTask)),
            "items": db.scalar(select(func.count()).select_from(ShopItem)),
            "messages": db.scalar(select(func.count()).select_from(ForumMessage)),
            "opening_ledger": db.scalar(
                select(func.count())
                .select_from(PointTransaction)
                .where(PointTransaction.transaction_type == "OPENING_BALANCE")
            ),
        }
        preserved_points = db.scalar(
            select(User.points).where(User.username == "123")
        )
        preserved_fill = db.scalar(
            select(BinContainer.last_fill_level).where(
                BinContainer.device_id == "municipal-prototype-001"
            )
        )
    assert after == before
    assert preserved_points == 77
    assert preserved_fill == pytest.approx(42.5)


def test_ema_updates_persistent_container_last_fill(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    responses = [
        client.post(
            "/api/sensors/ingest",
            json=telemetry_payload(device_id, distance),
        )
        for distance in (25.0, 7.0, 16.0)
    ]

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert [response.json()["fill_percent"] for response in responses] == pytest.approx(
        [0.0, 100.0, 85.0]
    )

    with session_factory() as db:
        container = db.scalar(
            select(BinContainer).where(BinContainer.device_id == device_id)
        )
        assert container is not None
        assert container.last_fill_level == pytest.approx(85.0)
        assert db.scalar(
            select(func.count())
            .select_from(Telemetry)
            .where(Telemetry.device_id == device_id)
        ) == 3

    map_row = next(
        row for row in client.get("/api/containers").json() if row["device_id"] == device_id
    )
    assert map_row["last_fill_level"] == pytest.approx(85.0)
    assert map_row["fill_percent"] == pytest.approx(85.0)


def test_retired_container_rejects_new_telemetry(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-rio-001"

    response = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload(device_id, 16.0, 51.0, 20.0),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Device is inactive"

    with session_factory() as db:
        assert db.scalar(
            select(func.count())
            .select_from(Telemetry)
            .where(Telemetry.device_id == device_id)
        ) == 0
        assert db.get(Device, device_id) is None


def test_temperature_above_50_sends_websocket_and_creates_alert(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-fire"

    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        baseline = client.post(
            "/api/sensors/ingest",
            json=telemetry_payload(device_id, 25.0, 20.0, 20.0),
        )
        hot = client.post(
            "/api/sensors/ingest",
            json=telemetry_payload(device_id, 16.0, 50.1, 20.0),
        )
        command_payload = websocket.receive_json()
        assert command_payload["action"] == "CLOSE_LID"
        assert command_payload["reason"] == "FIRE_RISK"
        assert isinstance(command_payload["command_id"], int)
        assert isinstance(command_payload["alert_id"], int)
        websocket.send_json(
            {
                "action": "COMMAND_ACK",
                "command_id": command_payload["command_id"],
            }
        )
        assert websocket.receive_json() == {
            "action": "ACK_CONFIRMED",
            "command_id": command_payload["command_id"],
            "reason": None,
        }

    assert baseline.json()["fire_streak"] == 0
    assert hot.json()["fire_streak"] == 1
    assert hot.json()["fire_risk"] is True
    assert hot.json()["action_triggered"] == "CLOSE_LID"
    assert hot.json()["command_sent"] is True

    with session_factory() as db:
        alerts = list(
            db.scalars(
                select(Alert).where(
                    Alert.device_id == device_id,
                    Alert.alert_type == "FIRE_RISK",
                )
            )
        )
        device = db.get(Device, device_id)
        command = db.get(DeviceCommand, command_payload["command_id"])
    assert len(alerts) == 1
    assert alerts[0].id == command_payload["alert_id"]
    assert alerts[0].status == "CRITICAL"
    assert alerts[0].is_resolved is False
    assert command is not None and command.status == "ACKED"
    assert device is not None and device.lid_status == "CLOSED"
    assert client.get(
        "/api/dispatch/summary", headers=DISPATCHER_HEADERS
    ).json()["total_unresolved"] == 1


def test_vision_upload_saves_frame_and_creates_illegal_dump_alert(api) -> None:
    client, session_factory, static_dir = api
    response = client.post(
        "/api/vision/frame",
        data={"device_id": "municipal-camera", "force_detect": "true"},
        files={"image": ("../../unsafe.png", PNG_1X1, "image/png")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detected"] is True
    assert body["object_label"] == "illegal_dump"
    assert body["alert_id"] is not None
    stored_path = static_dir / body["image_url"].removeprefix("/static/")
    assert stored_path.is_file()
    assert stored_path.read_bytes() == PNG_1X1
    assert "unsafe" not in stored_path.name

    with session_factory() as db:
        frame = db.get(VisionFrame, body["frame_id"])
        alert = db.get(Alert, body["alert_id"])
    assert frame is not None and frame.detected is True
    assert alert is not None and alert.alert_type == "ILLEGAL_DUMP"
    assert alert.evidence_path == frame.image_path


def test_bio_bread_approval_awards_15_in_ledger_and_opens_lid(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api
    monkeypatch.setattr(
        "app.api.bio.detect_objects",
        lambda _: [detected("sandwich")],
    )
    device_id = "bio-central-park-001"

    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        response = post_bio(
            client,
            device_id=device_id,
            idempotency_key="bio-approved-ws-001",
        )
        command_payload = websocket.receive_json()
        assert command_payload["action"] == "OPEN_LID"
        assert command_payload["analysis_id"] == response.json()["analysis_id"]
        assert isinstance(command_payload["command_id"], int)
        websocket.send_json(
            {
                "action": "COMMAND_ACK",
                "command_id": command_payload["command_id"],
            }
        )
        assert websocket.receive_json() == {
            "action": "ACK_CONFIRMED",
            "command_id": command_payload["command_id"],
            "reason": None,
        }

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "approve"
    assert body["reason"] is None
    assert body["points_awarded"] == 15
    assert body["current_balance"] == 135
    assert body["qr_code"].startswith("GOOD")
    assert body["action_triggered"] == "OPEN_LID"
    assert body["command_sent"] is True
    assert body["detected_objects"][0]["label"] == "sandwich"

    with session_factory() as db:
        analysis = db.get(BioAnalysis, body["analysis_id"])
        rewards = list(
            db.scalars(
                select(PointTransaction).where(
                    PointTransaction.transaction_type == "BIO_REWARD"
                )
            )
        )
        user = db.scalar(select(User).where(User.username == "123"))
        device = db.get(Device, device_id)
        command = db.get(DeviceCommand, command_payload["command_id"])
    assert analysis is not None and analysis.points == 15
    assert len(rewards) == 1
    assert rewards[0].amount == 15
    assert rewards[0].balance_after == 135
    assert rewards[0].reference_id == f"bio:{body['analysis_id']}"
    assert user is not None and user.points == 135
    assert command is not None and command.status == "ACKED"
    assert device is not None and device.lid_status == "OPEN"


def test_bio_idempotent_replay_reuses_analysis_qr_and_reward_but_conflict_is_409(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api
    inference_calls: list[str] = []

    def bread_detection(_):
        inference_calls.append("called")
        return [detected("sandwich")]

    monkeypatch.setattr("app.api.bio.detect_objects", bread_detection)
    operation_key = "bio-replay-operation-001"
    first = post_bio(client, idempotency_key=operation_key)
    replay = post_bio(client, idempotency_key=operation_key)
    conflict = post_bio(
        client,
        data=PNG_1X1_ALT,
        idempotency_key=operation_key,
    )

    assert first.status_code == replay.status_code == 200
    assert conflict.status_code == 409
    assert first.json()["analysis_id"] == replay.json()["analysis_id"]
    assert first.json()["qr_code"] == replay.json()["qr_code"]
    assert first.json()["current_balance"] == replay.json()["current_balance"] == 135
    assert len(inference_calls) == 1

    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(BioAnalysis)) == 1
        assert db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "BIO_REWARD")
        ) == 1
        assert db.scalar(
            select(func.count())
            .select_from(DeviceCommand)
            .where(DeviceCommand.action == "OPEN_LID")
        ) == 1
        assert db.scalar(select(User.points).where(User.username == "123")) == 135


def test_bio_idempotency_is_scoped_to_device_for_same_user_key_and_image(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api
    inference_calls: list[str] = []

    def bread_detection(_):
        inference_calls.append("called")
        return [detected("sandwich")]

    monkeypatch.setattr("app.api.bio.detect_objects", bread_detection)
    qr_values = iter((333, 444))
    monkeypatch.setattr(
        "app.api.bio.secrets.randbelow",
        lambda _: next(qr_values),
    )
    operation_key = "bio-device-scoped-key-001"
    first = post_bio(
        client,
        device_id="bio-central-park-001",
        idempotency_key=operation_key,
    )
    second = post_bio(
        client,
        device_id="bio-nish-fmn-001",
        idempotency_key=operation_key,
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["analysis_id"] != second.json()["analysis_id"]
    assert first.json()["qr_code"] != second.json()["qr_code"]
    assert first.json()["current_balance"] == 135
    assert second.json()["current_balance"] == 150
    assert len(inference_calls) == 2

    with session_factory() as db:
        analyses = list(db.scalars(select(BioAnalysis).order_by(BioAnalysis.id)))
        rewards = list(
            db.scalars(
                select(PointTransaction).where(
                    PointTransaction.transaction_type == "BIO_REWARD"
                )
            )
        )
    assert len(analyses) == 2
    assert {analysis.device_id for analysis in analyses} == {
        "bio-central-park-001",
        "bio-nish-fmn-001",
    }
    assert analyses[0].idempotency_key != analyses[1].idempotency_key
    assert len(rewards) == 2
    assert [reward.amount for reward in rewards] == [15, 15]


def test_bio_mold_has_priority_over_bread_and_awards_nothing(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api
    monkeypatch.setattr(
        "app.api.bio.detect_objects",
        lambda _: [detected("sandwich", 0.99), detected("broccoli", 0.75)],
    )

    response = post_bio(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "reject"
    assert body["reason"] == "mold_detected"
    assert body["points_awarded"] == 0
    assert body["current_balance"] == 120
    assert body["qr_code"].startswith("BAD")
    assert body["action_triggered"] is None
    assert body["command_sent"] is False

    with session_factory() as db:
        reward_count = db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "BIO_REWARD")
        )
        analysis = db.get(BioAnalysis, body["analysis_id"])
    assert reward_count == 0
    assert analysis is not None and analysis.status == "reject"
    assert analysis.points == 0


def test_bio_nonbread_is_invalid_without_points_and_qr_codes_are_unique(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api
    monkeypatch.setattr(
        "app.api.bio.detect_objects",
        lambda _: [detected("bottle")],
    )
    qr_values = iter((111, 222))
    monkeypatch.setattr(
        "app.api.bio.secrets.randbelow",
        lambda _: next(qr_values),
    )

    first = post_bio(client, idempotency_key="bio-nonbread-001")
    second = post_bio(client, idempotency_key="bio-nonbread-002")
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "invalid"
    assert first.json()["reason"] == second.json()["reason"] == "not_bread"
    assert first.json()["points_awarded"] == second.json()["points_awarded"] == 0
    assert first.json()["current_balance"] == second.json()["current_balance"] == 120
    assert {first.json()["qr_code"], second.json()["qr_code"]} == {
        "NONE100111",
        "NONE100222",
    }

    with session_factory() as db:
        assert db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "BIO_REWARD")
        ) == 0
        assert db.scalar(select(func.count()).select_from(BioAnalysis)) == 2
        assert db.scalar(
            select(func.count(func.distinct(BioAnalysis.qr_code)))
        ) == 2


def test_bio_empty_multipart_file_returns_invalid_without_running_yolo(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api

    def should_not_run(_):
        raise AssertionError("YOLO must not run for an empty upload")

    monkeypatch.setattr("app.api.bio.detect_objects", should_not_run)
    response = post_bio(client, data=b"")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "invalid"
    assert body["reason"] == "empty_frame"
    assert body["points_awarded"] == 0
    assert body["current_balance"] == 120
    assert body["image_url"] is None
    assert body["detected_objects"] == []
    assert body["action_triggered"] is None

    with session_factory() as db:
        analysis = db.get(BioAnalysis, body["analysis_id"])
        reward_count = db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "BIO_REWARD")
        )
    assert analysis is not None and analysis.image_path is None
    assert reward_count == 0


def test_device_kind_interlocks_reject_bio_on_municipal_and_sensors_on_bio(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api

    def should_not_run(_):
        raise AssertionError("YOLO must not run after a device-kind conflict")

    monkeypatch.setattr("app.api.bio.detect_objects", should_not_run)
    bio_on_municipal = post_bio(
        client,
        device_id="municipal-prototype-001",
        idempotency_key="kind-conflict-bio-001",
    )
    sensors_on_bio = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload("bio-central-park-001", 55.0),
    )
    assert bio_on_municipal.status_code == 409
    assert sensors_on_bio.status_code == 409

    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(BioAnalysis)) == 0
        assert db.scalar(select(func.count()).select_from(Telemetry)) == 0


def test_decoded_image_over_pixel_limit_returns_413(
    api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session_factory, _ = api

    def should_not_run(_):
        raise AssertionError("YOLO must not run for an oversized decoded image")

    monkeypatch.setattr("app.api.bio.detect_objects", should_not_run)
    response = post_bio(
        client,
        data=make_png(size=(11, 10)),
        idempotency_key="pixel-limit-image-001",
    )
    assert response.status_code == 413
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(BioAnalysis)) == 0


def test_upload_body_over_byte_limit_returns_413(api) -> None:
    client, session_factory, _ = api
    response = post_bio(
        client,
        data=b"x" * 2048,
        idempotency_key="body-limit-image-001",
    )
    assert response.status_code == 413
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(BioAnalysis)) == 0


def test_nft_mints_are_unique_debit_points_and_appear_in_collection_and_history(api) -> None:
    client, session_factory, _ = api
    with session_factory() as db:
        owner = db.scalar(select(User).where(User.username == "Айгерім"))
        assert owner is not None
        owner_reference = str(owner.id)

    first = client.post(
        "/api/shop/mint-nft",
        json={
            "user_id": owner_reference,
            "title": "Green Leaf Alpha",
            "idempotency_key": "nft-green-alpha-001",
        },
    )
    replay = client.post(
        "/api/shop/mint-nft",
        json={
            "user_id": owner_reference,
            "title": "Green Leaf Alpha",
            "idempotency_key": "nft-green-alpha-001",
        },
    )
    second = client.post(
        "/api/shop/mint-nft",
        json={
            "user_id": owner_reference,
            "title": "Green Leaf Beta",
            "idempotency_key": "nft-green-beta-001",
        },
    )
    assert first.status_code == replay.status_code == second.status_code == 200
    first_body, second_body = first.json(), second.json()
    assert replay.json()["nft"]["id"] == first_body["nft"]["id"]
    assert replay.json()["nft"]["token_id"] == first_body["nft"]["token_id"]
    assert replay.json()["current_balance"] == first_body["current_balance"] == 180
    assert first_body["price_points"] == second_body["price_points"] == 100
    assert first_body["current_balance"] == 180
    assert second_body["current_balance"] == 80
    assert first_body["nft"]["token_id"] != second_body["nft"]["token_id"]
    assert first_body["nft"]["svg_content"] != second_body["nft"]["svg_content"]
    ElementTree.fromstring(first_body["nft"]["svg_content"])
    ElementTree.fromstring(second_body["nft"]["svg_content"])

    collection = client.get(f"/api/users/{owner_reference}/nfts")
    history = client.get(f"/api/users/{owner_reference}/transactions")
    dashboard = client.get(f"/api/users/{owner_reference}/dashboard")
    assert collection.status_code == history.status_code == dashboard.status_code == 200
    assert {row["token_id"] for row in collection.json()} == {
        first_body["nft"]["token_id"],
        second_body["nft"]["token_id"],
    }
    nft_transactions = [
        row for row in history.json() if row["transaction_type"] == "NFT_MINT"
    ]
    assert len(nft_transactions) == 2
    assert [row["amount"] for row in nft_transactions] == [-100, -100]
    assert len(dashboard.json()["nfts"]) == 2

    with session_factory() as db:
        owner = db.get(User, int(owner_reference))
        assert owner is not None and owner.points == 80
        assert db.scalar(
            select(func.count()).select_from(EcoNFT).where(EcoNFT.owner_id == owner.id)
        ) == 2


def test_nft_insufficient_balance_rolls_back_nft_and_ledger(api) -> None:
    client, session_factory, _ = api
    response = client.post(
        "/api/shop/mint-nft",
        json={
            "user_id": "volunteer-1",
            "title": "Cannot Afford",
            "idempotency_key": "nft-insufficient-001",
        },
    )
    assert response.status_code == 409

    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "volunteer-1"))
        assert user is not None and user.points == 40
        assert db.scalar(
            select(func.count()).select_from(EcoNFT).where(EcoNFT.owner_id == user.id)
        ) == 0
        assert db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(
                PointTransaction.user_id == user.id,
                PointTransaction.transaction_type == "NFT_MINT",
            )
        ) == 0


def test_nft_svg_escapes_untrusted_title_and_contains_no_executable_markup(api) -> None:
    client, _, _ = api
    malicious = '</text><script>alert(1)</script><text onload="evil()">&leaf'
    response = client.post(
        "/api/shop/mint-nft",
        json={
            "user_id": "123",
            "title": malicious,
            "idempotency_key": "nft-xss-safe-001",
        },
    )
    assert response.status_code == 200, response.text
    svg = response.json()["nft"]["svg_content"]
    root = ElementTree.fromstring(svg)

    assert "<script" not in svg.casefold()
    assert "javascript:" not in svg.casefold()
    assert "&lt;script&gt;" in svg
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1].casefold()
        assert local_name != "script"
        assert all(not name.casefold().startswith("on") for name in element.attrib)
        assert all("javascript:" not in value.casefold() for value in element.attrib.values())


def test_volunteer_registers_without_reward_then_completes_exactly_once(api) -> None:
    client, session_factory, _ = api
    task = client.get("/api/volunteer/tasks").json()[0]
    reward = task["reward_points"]

    registered = client.post(
        f"/api/volunteer/tasks/{task['id']}/register",
        json={"user_id": "volunteer-1"},
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["reward_points_pending"] == reward
    assert registered.json()["points_balance"] == 40

    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "volunteer-1"))
        assert user is not None and user.points == 40
        user_task = db.scalar(
            select(UserTask).where(
                UserTask.user_id == user.id,
                UserTask.task_id == task["id"],
            )
        )
        assert user_task is not None
        assert user_task.status == "registered"
        assert user_task.reward_points_awarded == 0
        assert db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "VOLUNTEER_REWARD")
        ) == 0

    completed = client.post(
        f"/api/volunteer/tasks/{task['id']}/complete",
        headers=DISPATCHER_HEADERS,
        json={
            "user_id": "volunteer-1",
            "dispatcher_id": "dispatcher-1",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["points_awarded"] == reward
    assert completed.json()["current_balance"] == 40 + reward

    duplicate = client.post(
        f"/api/volunteer/tasks/{task['id']}/complete",
        headers=DISPATCHER_HEADERS,
        json={
            "user_id": "volunteer-1",
            "dispatcher_id": "dispatcher-1",
        },
    )
    assert duplicate.status_code == 409

    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "volunteer-1"))
        assert user is not None and user.points == 40 + reward
        user_task = db.scalar(
            select(UserTask).where(
                UserTask.user_id == user.id,
                UserTask.task_id == task["id"],
            )
        )
        rewards = list(
            db.scalars(
                select(PointTransaction).where(
                    PointTransaction.user_id == user.id,
                    PointTransaction.transaction_type == "VOLUNTEER_REWARD",
                )
            )
        )
    assert user_task is not None and user_task.status == "completed"
    assert user_task.reward_points_awarded == reward
    assert len(rewards) == 1 and rewards[0].amount == reward


def test_volunteer_endpoints_require_volunteer_role(api) -> None:
    client, session_factory, _ = api
    task = client.get("/api/volunteer/tasks").json()[0]
    registered = client.post(
        f"/api/volunteer/tasks/{task['id']}/register",
        json={"user_id": "123"},
    )
    completed = client.post(
        f"/api/volunteer/tasks/{task['id']}/complete",
        headers=DISPATCHER_HEADERS,
        json={"user_id": "123", "dispatcher_id": "dispatcher-1"},
    )
    assert registered.status_code == 403
    assert completed.status_code == 403
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(UserTask)) == 0


def test_volunteer_completion_without_dispatcher_key_is_401_and_awards_nothing(api) -> None:
    client, session_factory, _ = api
    task = client.get("/api/volunteer/tasks").json()[0]
    registered = client.post(
        f"/api/volunteer/tasks/{task['id']}/register",
        json={"user_id": "volunteer-1"},
    )
    assert registered.status_code == 201

    completed = client.post(
        f"/api/volunteer/tasks/{task['id']}/complete",
        json={
            "user_id": "volunteer-1",
            "dispatcher_id": "dispatcher-1",
        },
    )
    assert completed.status_code == 401
    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "volunteer-1"))
        user_task = db.scalar(select(UserTask))
        assert user is not None and user.points == 40
        assert user_task is not None and user_task.status == "registered"
        assert db.scalar(
            select(func.count())
            .select_from(PointTransaction)
            .where(PointTransaction.transaction_type == "VOLUNTEER_REWARD")
        ) == 0


def test_shop_purchase_debit_and_ledger_are_atomic_on_insufficient_retry(api) -> None:
    client, session_factory, _ = api
    item = client.get("/api/shop/items").json()[-1]
    assert item["price_points"] == 90

    payload = {
        "user_id": "123",
        "item_id": item["id"],
        "idempotency_key": "shop-purchase-replay-001",
    }
    purchased = client.post("/api/shop/buy", json=payload)
    assert purchased.status_code == 200, purchased.text
    assert purchased.json()["spent_points"] == 90
    assert purchased.json()["points_balance"] == 30

    replay = client.post("/api/shop/buy", json=payload)
    assert replay.status_code == 200
    assert replay.json()["purchase_id"] == purchased.json()["purchase_id"]
    assert replay.json()["points_balance"] == 30

    insufficient = client.post(
        "/api/shop/buy",
        json={
            "user_id": "123",
            "item_id": item["id"],
            "idempotency_key": "shop-purchase-second-001",
        },
    )
    assert insufficient.status_code == 409

    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "123"))
        assert user is not None and user.points == 30
        purchases = list(
            db.scalars(select(ShopPurchase).where(ShopPurchase.user_id == user.id))
        )
        debits = list(
            db.scalars(
                select(PointTransaction).where(
                    PointTransaction.user_id == user.id,
                    PointTransaction.transaction_type == "SHOP_PURCHASE",
                )
            )
        )
    assert len(purchases) == 1
    assert len(debits) == 1
    assert debits[0].amount == -90 and debits[0].balance_after == 30


def test_shop_and_nft_mutations_require_idempotency_keys(api) -> None:
    client, session_factory, _ = api
    item = client.get("/api/shop/items").json()[0]
    missing_shop_key = client.post(
        "/api/shop/buy",
        json={"user_id": "123", "item_id": item["id"]},
    )
    missing_nft_key = client.post(
        "/api/shop/mint-nft",
        json={"user_id": "123", "title": "Missing key"},
    )
    assert missing_shop_key.status_code == 422
    assert missing_nft_key.status_code == 422
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ShopPurchase)) == 0
        assert db.scalar(select(func.count()).select_from(EcoNFT)) == 0


def test_dispatcher_and_dispatch_endpoints_without_api_key_return_401(api) -> None:
    client, session_factory, _ = api
    command = client.post(
        "/api/dispatcher/devices/municipal-prototype-001/command",
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "CLOSE_LID",
            "idempotency_key": "missing-api-key-001",
        },
    )
    summary = client.get("/api/dispatch/summary")
    assert command.status_code == summary.status_code == 401
    assert command.headers["www-authenticate"] == "ApiKey"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DeviceCommand)) == 0


def test_dispatcher_command_requires_dispatcher_role(api) -> None:
    client, session_factory, _ = api
    response = client.post(
        "/api/dispatcher/devices/municipal-prototype-001/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "123",
            "action": "CLOSE_LID",
            "idempotency_key": "role-denied-001",
        },
    )
    assert response.status_code == 403
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DeviceCommand)) == 0


def test_dispatcher_command_is_idempotent_while_device_is_offline(api) -> None:
    client, session_factory, _ = api
    endpoint = "/api/dispatcher/devices/municipal-prototype-001/command"
    payload = {
        "dispatcher_id": "dispatcher-1",
        "action": "CLOSE_LID",
        "idempotency_key": "offline-idempotent-001",
    }
    first = client.post(endpoint, headers=DISPATCHER_HEADERS, json=payload)
    replay = client.post(endpoint, headers=DISPATCHER_HEADERS, json=payload)
    conflict = client.post(
        endpoint,
        headers=DISPATCHER_HEADERS,
        json={**payload, "action": "OPEN_LID"},
    )

    assert first.status_code == replay.status_code == 200
    assert first.json()["status"] == replay.json()["status"] == "PENDING"
    assert first.json()["command_sent"] is replay.json()["command_sent"] is False
    assert first.json()["id"] == replay.json()["id"]
    assert conflict.status_code == 409
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DeviceCommand)) == 1


def test_dispatcher_key_cannot_collide_with_internal_fire_namespace(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    manual = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "CLOSE_LID",
            "idempotency_key": "fire-alert:1",
        },
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["idempotency_key"] == "fire-alert:1"

    hot = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload(device_id, 16.0, 50.1, 20.0),
    )
    assert hot.status_code == 200, hot.text

    with session_factory() as db:
        keys = set(db.scalars(select(DeviceCommand.idempotency_key)).all())
        fire_alert = db.scalar(
            select(Alert).where(Alert.alert_type == "FIRE_RISK")
        )
    assert "dispatcher:fire-alert:1" in keys
    assert fire_alert is not None
    assert f"fire-alert:{fire_alert.id}" in keys


def test_unacked_sent_command_is_redelivered_on_reconnect_then_acked(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    response = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "CLOSE_LID",
            "idempotency_key": "durable-close-001",
        },
    )
    assert response.status_code == 200, response.text
    command_id = response.json()["id"]
    assert response.json()["status"] == "PENDING"
    assert response.json()["command_sent"] is False

    expected_payload = {
        "action": "CLOSE_LID",
        "command_id": command_id,
        "idempotency_key": "durable-close-001",
    }
    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        assert websocket.receive_json() == expected_payload

    with session_factory() as db:
        unacked = db.get(DeviceCommand, command_id)
        assert unacked is not None and unacked.status == "SENT"
        assert unacked.acknowledged_at is None

    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        redelivered = websocket.receive_json()
        assert redelivered == {
            "action": "CLOSE_LID",
            "command_id": command_id,
            "idempotency_key": "durable-close-001",
        }
        websocket.send_json({"action": "COMMAND_ACK", "command_id": command_id})
        assert websocket.receive_json() == {
            "action": "ACK_CONFIRMED",
            "command_id": command_id,
            "reason": None,
        }

    with session_factory() as db:
        command = db.get(DeviceCommand, command_id)
        device = db.get(Device, device_id)
    assert command is not None and command.status == "ACKED"
    assert command.attempts >= 3
    assert command.sent_at is not None and command.acknowledged_at is not None
    assert device is not None and device.lid_status == "CLOSED"


def test_ack_of_newer_command_supersedes_older_unacked_commands(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    first = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "CLOSE_LID",
            "idempotency_key": "older-close-before-newer-ack-001",
        },
    )
    second = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "OPEN_LID",
            "idempotency_key": "newer-open-that-is-acked-001",
        },
    )
    assert first.status_code == second.status_code == 200
    first_id = first.json()["id"]
    second_id = second.json()["id"]
    assert first_id < second_id

    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        assert websocket.receive_json()["command_id"] == first_id
        assert websocket.receive_json()["command_id"] == second_id
        websocket.send_json({"action": "COMMAND_ACK", "command_id": second_id})
        assert websocket.receive_json() == {
            "action": "ACK_CONFIRMED",
            "command_id": second_id,
            "reason": None,
        }

    with session_factory() as db:
        older = db.get(DeviceCommand, first_id)
        newer = db.get(DeviceCommand, second_id)
        device = db.get(Device, device_id)
    assert older is not None and older.status == "FAILED"
    assert older.last_error == f"superseded_by_ack:{second_id}"
    assert newer is not None and newer.status == "ACKED"
    assert device is not None and device.lid_status == "OPEN"


def test_slow_device_send_times_out_and_unregisters(monkeypatch) -> None:
    class SlowSocket:
        async def send_json(self, payload) -> None:  # noqa: ARG002
            await asyncio.sleep(60)

    monkeypatch.setattr(
        websocket_service,
        "settings",
        SimpleNamespace(websocket_send_timeout_seconds=0.01),
    )

    async def scenario() -> bool:
        socket = SlowSocket()
        await websocket_service.register_device("slow-device", socket)  # type: ignore[arg-type]
        return await websocket_service.send_device_command(
            "slow-device", {"action": "CLOSE_LID"}
        )

    assert asyncio.run(scenario()) is False
    assert "slow-device" not in websocket_service.connected_devices


def test_active_fire_alert_resolves_only_after_cooldown_resets_streak(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-resolve-cooldown"
    first_hot = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload(device_id, 16.0, 50.1, 20.0),
    )
    assert first_hot.status_code == 200
    assert first_hot.json()["fire_streak"] == 1

    with session_factory() as db:
        alert = db.scalar(
            select(Alert).where(
                Alert.device_id == device_id,
                Alert.alert_type == "FIRE_RISK",
                Alert.is_resolved.is_(False),
            )
        )
        assert alert is not None
        alert_id = alert.id

    blocked = client.patch(
        f"/api/alerts/{alert_id}/resolve",
        headers=DISPATCHER_HEADERS,
    )
    assert blocked.status_code == 409
    assert "cooldown" in blocked.json()["detail"].casefold()

    cooldown = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload(device_id, 16.0, 50.0, 20.0),
    )
    assert cooldown.status_code == 200
    assert cooldown.json()["fire_streak"] == 0

    resolved = client.patch(
        f"/api/alerts/{alert_id}/resolve",
        headers=DISPATCHER_HEADERS,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    with session_factory() as db:
        persisted_alert = db.get(Alert, alert_id)
        device = db.get(Device, device_id)
    assert persisted_alert is not None and persisted_alert.is_resolved is True
    assert persisted_alert.status == "RESOLVED"
    assert device is not None and device.fire_streak == 0


def test_unresolved_fire_risk_blocks_dispatcher_open_command(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    with session_factory() as db:
        db.add(
            Alert(
                device_id=device_id,
                alert_type="FIRE_RISK",
                status="CRITICAL",
                message="active fire",
            )
        )
        db.commit()

    response = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "OPEN_LID",
            "idempotency_key": "blocked-open-001",
        },
    )
    assert response.status_code == 409
    assert "fire risk" in response.json()["detail"].casefold().replace("_", " ")
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(DeviceCommand)) == 0


def test_fire_supersedes_offline_open_and_reconnect_delivers_only_close(api) -> None:
    client, session_factory, _ = api
    device_id = "municipal-prototype-001"
    open_response = client.post(
        f"/api/dispatcher/devices/{device_id}/command",
        headers=DISPATCHER_HEADERS,
        json={
            "dispatcher_id": "dispatcher-1",
            "action": "OPEN_LID",
            "idempotency_key": "offline-open-before-fire-001",
        },
    )
    assert open_response.status_code == 200, open_response.text
    assert open_response.json()["status"] == "PENDING"
    assert open_response.json()["command_sent"] is False
    open_command_id = open_response.json()["id"]

    first_hot = client.post(
        "/api/sensors/ingest",
        json=telemetry_payload(device_id, 16.0, 50.1, 20.0),
    )
    assert first_hot.status_code == 200
    assert first_hot.json()["fire_streak"] == 1
    assert first_hot.json()["action_triggered"] == "CLOSE_LID"
    assert first_hot.json()["command_sent"] is False

    with session_factory() as db:
        open_command = db.get(DeviceCommand, open_command_id)
        close_command = db.scalar(
            select(DeviceCommand).where(
                DeviceCommand.device_id == device_id,
                DeviceCommand.action == "CLOSE_LID",
            )
        )
        fire_alert = db.scalar(
            select(Alert).where(
                Alert.device_id == device_id,
                Alert.alert_type == "FIRE_RISK",
                Alert.is_resolved.is_(False),
            )
        )
    assert open_command is not None and open_command.status == "FAILED"
    assert open_command.last_error == "superseded_by_fire_risk"
    assert close_command is not None and close_command.status == "PENDING"
    assert fire_alert is not None

    with client.websocket_connect(f"/ws/device/{device_id}") as websocket:
        delivered = websocket.receive_json()
        assert delivered["action"] == "CLOSE_LID"
        assert delivered["command_id"] == close_command.id
        assert delivered["reason"] == "FIRE_RISK"
        assert delivered["alert_id"] == fire_alert.id

        websocket.send_json(
            {"action": "COMMAND_ACK", "command_id": open_command_id}
        )
        assert websocket.receive_json() == {
            "action": "ERROR",
            "command_id": open_command_id,
            "reason": "command_not_found",
        }
        with session_factory() as db:
            rejected_open = db.get(DeviceCommand, open_command_id)
            interlocked_device = db.get(Device, device_id)
        assert rejected_open is not None and rejected_open.status == "FAILED"
        assert interlocked_device is not None
        assert interlocked_device.lid_status != "OPEN"

        websocket.send_json(
            {"action": "COMMAND_ACK", "command_id": close_command.id}
        )
        assert websocket.receive_json() == {
            "action": "ACK_CONFIRMED",
            "command_id": close_command.id,
            "reason": None,
        }
        websocket.send_json({"action": "PING"})
        assert websocket.receive_json() == {"action": "PONG"}

    with session_factory() as db:
        persisted_open = db.get(DeviceCommand, open_command_id)
        persisted_close = db.get(DeviceCommand, close_command.id)
        device = db.get(Device, device_id)
    assert persisted_open is not None and persisted_open.status == "FAILED"
    assert persisted_close is not None and persisted_close.status == "ACKED"
    assert device is not None and device.lid_status == "CLOSED"


def test_community_ai_chat_and_cors(api) -> None:
    client, _, _ = api
    posted = client.post(
        "/api/community/chat",
        json={"username": "123", "text": "  Где ближайший контейнер?  "},
    )
    assert posted.status_code == 201
    assert posted.json()["text"] == "Где ближайший контейнер?"
    messages = client.get("/api/community/chat", params={"limit": 1})
    assert messages.status_code == 200
    assert messages.json()[-1]["id"] == posted.json()["id"]

    answer = client.post(
        "/api/ai/chat",
        json={"user_id": "123", "message": "Как найти контейнер для хлеба?"},
    )
    assert answer.status_code == 200
    assert set(answer.json()) == {"response", "provider", "model"}
    assert "123" in answer.json()["response"]

    allowed = client.options(
        "/api/shop/mint-nft",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3001"

    rejected = client.options(
        "/api/shop/mint-nft",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in rejected.headers


def test_gemini_sdk_call_runs_outside_event_loop_thread(monkeypatch) -> None:
    caller_thread = threading.get_ident()
    observed: dict[str, object] = {}

    class FakeResponse:
        text = "Персональный ответ Баки"

    class FakeModel:
        def generate_content(self, prompt, **kwargs):  # type: ignore[no-untyped-def]
            observed["thread"] = threading.get_ident()
            observed["prompt"] = prompt
            observed["kwargs"] = kwargs
            return FakeResponse()

    bot = GeminiBot(
        api_key="test-key",
        model_name="gemini-3.5-flash",
        timeout_seconds=1.0,
        max_output_tokens=200,
    )
    monkeypatch.setattr(bot, "_get_or_create_model", lambda: FakeModel())
    context = GeminiUserContext(
        username="volunteer-1",
        role="volunteer",
        points=40,
        status_tier="Eco-Volunteer",
    )

    reply = asyncio.run(bot.reply("Как помочь городу?", context))

    assert reply.text == "Персональный ответ Баки"
    assert reply.provider == "google-gemini"
    assert reply.model == "gemini-3.5-flash"
    assert observed["thread"] != caller_thread
    assert "volunteer-1" in str(observed["prompt"])
    assert "Как помочь городу?" in str(observed["prompt"])


def test_gemini_failure_degrades_to_role_aware_fallback(monkeypatch) -> None:
    class FailingModel:
        def generate_content(self, prompt, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("quota unavailable")

    bot = GeminiBot(
        api_key="test-key",
        model_name="gemini-3.5-flash",
        timeout_seconds=1.0,
        max_output_tokens=200,
    )
    monkeypatch.setattr(bot, "_get_or_create_model", lambda: FailingModel())
    context = GeminiUserContext(
        username="dispatcher-1",
        role="dispatcher",
        points=0,
        status_tier="Dispatcher",
    )

    reply = asyncio.run(bot.reply("Что проверить?", context))

    assert reply.provider == "offline-fallback"
    assert reply.model is None
    assert "dispatcher-1" in reply.text
    assert "пожар" in reply.text.casefold()
