from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base
from app.models import Alert, Device, VisionFrame
from app.services import camera_vision
from app.services.yolo import DetectedObject


def test_capture_url_uses_esp32_control_server() -> None:
    assert (
        camera_vision.capture_url_from_stream("http://192.168.10.29:81/stream")
        == "http://192.168.10.29/capture"
    )
    assert (
        camera_vision.capture_url_from_stream("http://camera.local:8080/stream")
        == "http://camera.local:8080/capture"
    )


def test_camera_analysis_saves_boxes_and_deduplicates_open_alert(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'camera.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )
    static_dir = tmp_path / "static"
    test_settings = replace(
        settings,
        static_dir=static_dir,
        camera_frame_retention=10,
        camera_alert_cooldown_seconds=300,
    )
    monkeypatch.setattr(camera_vision, "settings", test_settings)

    def fake_download(_: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (320, 240), "white").save(destination, "JPEG")

    monkeypatch.setattr(camera_vision, "_download_snapshot", fake_download)
    monkeypatch.setattr(
        camera_vision,
        "detect_objects",
        lambda _: [
            DetectedObject(
                label="bottle",
                confidence=0.91,
                bounding_box=[40.0, 30.0, 180.0, 210.0],
            )
        ],
    )

    with session_factory() as db:
        db.add(
            Device(
                id="municipal-camera-test",
                kind="municipal",
                camera_stream_url="http://192.168.1.50:81/stream",
            )
        )
        db.commit()

        first = camera_vision.analyze_device_by_id(db, "municipal-camera-test")
        second = camera_vision.analyze_device_by_id(db, "municipal-camera-test")

        assert first.detected is True
        assert first.confidence == 0.91
        assert first.alert_id is not None
        assert second.alert_id == first.alert_id
        assert (static_dir / first.image_path).is_file()
        assert db.scalar(select(func.count()).select_from(VisionFrame)) == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(Alert)
                .where(Alert.alert_type == "ILLEGAL_DUMP")
            )
            == 1
        )

    engine.dispose()
