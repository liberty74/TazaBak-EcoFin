"""Take one municipal device out of service and purge its dynamic demo data.

Usage from the backend directory:
    ./.venv/Scripts/python.exe scripts/decommission_device.py

The script is intentionally scoped to one explicit device ID. It deactivates
the container, removes its telemetry, alerts, commands and camera frames, and
clears only evidence files belonging to those records.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Alert,
    BinContainer,
    Device,
    DeviceCommand,
    Telemetry,
    UserTask,
    VisionFrame,
    VolunteerTask,
)
from app.services.seed import seed_initial_data  # noqa: E402


LOGGER = logging.getLogger("tazabak.decommission")


def _remove_evidence_files(relative_paths: set[str]) -> int:
    static_root = settings.static_dir.resolve()
    removed = 0
    for relative_path in relative_paths:
        candidate = (static_root / relative_path).resolve()
        if not candidate.is_relative_to(static_root):
            LOGGER.warning("Skipped unsafe evidence path: %s", relative_path)
            continue
        if candidate.is_file():
            candidate.unlink()
            removed += 1
    return removed


def deactivate_and_purge(device_id: str) -> dict[str, int]:
    """Deactivate one device and return counts of cleaned dynamic records."""

    with SessionLocal() as db:
        device = db.get(Device, device_id)
        container = db.scalar(
            select(BinContainer).where(BinContainer.device_id == device_id)
        )
        if device is None or container is None:
            raise RuntimeError(f"Municipal container {device_id!r} was not found")

        frames = list(
            db.scalars(
                select(VisionFrame).where(VisionFrame.device_id == device_id)
            ).all()
        )
        alerts = list(
            db.scalars(select(Alert).where(Alert.device_id == device_id)).all()
        )
        evidence_paths = {
            path
            for path in (
                *(frame.image_path for frame in frames),
                *(alert.evidence_path for alert in alerts),
            )
            if path
        }

        counts = {
            "telemetry": db.execute(
                delete(Telemetry).where(Telemetry.device_id == device_id)
            ).rowcount
            or 0,
            "commands": db.execute(
                delete(DeviceCommand).where(DeviceCommand.device_id == device_id)
            ).rowcount
            or 0,
            "frames": db.execute(
                delete(VisionFrame).where(VisionFrame.device_id == device_id)
            ).rowcount
            or 0,
            "alerts": db.execute(
                delete(Alert).where(Alert.device_id == device_id)
            ).rowcount
            or 0,
        }
        container.is_active = False
        container.last_fill_level = 0.0
        device.fire_streak = 0
        device.lid_status = "DISABLED"
        device.camera_stream_url = None
        # Remove the retired node itself, so it cannot appear in any status list.
        db.delete(container)
        db.delete(device)

        legacy_task_titles = {
            "Очистка территории вокруг бака ТЦ РИО": (
                "Очистка территории вокруг демонстрационного бака",
                "Убрать территорию вокруг макета TazaBAK и сообщить о повреждениях.",
            ),
            "Дежурство у бокса ТЦ РИО": (
                "Дежурство у демонстрационного бокса",
                "Подсказать посетителям правила сдачи хлеба в течение часа.",
            ),
        }
        for old_title, (new_title, new_description) in legacy_task_titles.items():
            old_task = db.scalar(
                select(VolunteerTask).where(VolunteerTask.title == old_title)
            )
            if old_task is None:
                continue

            new_task = db.scalar(
                select(VolunteerTask).where(VolunteerTask.title == new_title)
            )
            if new_task is None:
                old_task.title = new_title
                old_task.description = new_description
                continue

            # A hot reload may already have seeded the replacement task. Move
            # registrations where possible, then remove the legacy TЦ РИО row.
            new_task_user_ids = set(
                db.scalars(
                    select(UserTask.user_id).where(UserTask.task_id == new_task.id)
                ).all()
            )
            for registration in db.scalars(
                select(UserTask).where(UserTask.task_id == old_task.id)
            ):
                if registration.user_id in new_task_user_ids:
                    db.delete(registration)
                else:
                    registration.task_id = new_task.id
            db.flush()
            db.delete(old_task)
        db.commit()

    # Ensure the active prototype is available after retiring the old node.
    seed_initial_data(SessionLocal)
    counts["files"] = _remove_evidence_files(evidence_paths)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device-id",
        default="municipal-rio-001",
        help="Municipal device to deactivate and purge",
    )
    args = parser.parse_args()
    counts = deactivate_and_purge(args.device_id)
    LOGGER.info("Decommissioned device=%s: %s", args.device_id, counts)
    print(f"Decommissioned {args.device_id}: {counts}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
