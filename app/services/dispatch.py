"""Dispatcher aggregation and deterministic LLM mock."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models import Alert, utcnow
from app.schemas import DispatchAlert, DispatchBriefing, DispatchSummary


STATUS_PRIORITY = {"CRITICAL": 1, "HIGH": 2, "WARNING": 3, "INFO": 4}


def _evidence_url(path: str | None) -> str | None:
    return f"/static/{path}" if path else None


def get_unresolved_alerts(db: Session) -> list[Alert]:
    priority = case(
        STATUS_PRIORITY,
        value=Alert.status,
        else_=99,
    )
    return list(
        db.scalars(
            select(Alert)
            .where(Alert.is_resolved.is_(False))
            .order_by(priority.asc(), Alert.created_at.asc(), Alert.id.asc())
        ).all()
    )


def build_summary(db: Session) -> DispatchSummary:
    alerts = get_unresolved_alerts(db)
    return DispatchSummary(
        generated_at=utcnow(),
        total_unresolved=len(alerts),
        counts_by_type=dict(Counter(alert.alert_type for alert in alerts)),
        counts_by_status=dict(Counter(alert.status for alert in alerts)),
        tasks=[
            DispatchAlert(
                id=alert.id,
                device_id=alert.device_id,
                type=alert.alert_type,
                status=alert.status,
                message=alert.message,
                evidence_url=_evidence_url(alert.evidence_path),
                details=alert.details,
                created_at=alert.created_at,
            )
            for alert in alerts
        ],
    )


def build_mock_llm_briefing(db: Session) -> DispatchBriefing:
    alerts = get_unresolved_alerts(db)
    generated_at = utcnow()
    if not alerts:
        return DispatchBriefing(
            generated_at=generated_at,
            total_tasks=0,
            text="Активных инцидентов нет. Все городские узлы работают штатно.",
        )

    lines = ["Приоритетный план для диспетчера TazaBAK:"]
    for number, alert in enumerate(alerts, start=1):
        if alert.alert_type == "FIRE_RISK":
            action = "немедленно проверить бак и подтвердить закрытие крышки"
        elif alert.alert_type == "ILLEGAL_DUMP":
            action = "направить бригаду и проверить приложенный кадр"
        else:
            action = "проверить инцидент и назначить исполнителя"
        lines.append(
            f"{number}. [{alert.status}] {alert.device_id or 'unknown'}: "
            f"{action} (alert #{alert.id})."
        )

    return DispatchBriefing(
        generated_at=generated_at,
        total_tasks=len(alerts),
        text="\n".join(lines),
    )
