"""Dispatcher summary, briefing and alert lifecycle endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Device, utcnow
from app.schemas import (
    DispatchBriefing,
    DispatchSummary,
    ResolveAlertResponse,
)
from app.security import require_dispatcher_key
from app.services.dispatch import build_mock_llm_briefing, build_summary


logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["dispatch"], dependencies=[Depends(require_dispatcher_key)]
)


@router.get("/api/dispatch/summary", response_model=DispatchSummary)
def dispatch_summary(db: Session = Depends(get_db)) -> DispatchSummary:
    try:
        return build_summary(db)
    except SQLAlchemyError as exc:
        logger.exception("Could not build dispatcher summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dispatcher summary is temporarily unavailable",
        ) from exc


@router.get("/api/dispatch/briefing", response_model=DispatchBriefing)
def dispatch_briefing(db: Session = Depends(get_db)) -> DispatchBriefing:
    """Return a deterministic text response that mimics an LLM dispatcher."""

    try:
        return build_mock_llm_briefing(db)
    except SQLAlchemyError as exc:
        logger.exception("Could not build dispatcher briefing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dispatcher briefing is temporarily unavailable",
        ) from exc


@router.patch(
    "/api/alerts/{alert_id}/resolve", response_model=ResolveAlertResponse
)
def resolve_alert(
    alert_id: int, db: Session = Depends(get_db)
) -> ResolveAlertResponse:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    if alert.alert_type == "FIRE_RISK" and alert.device_id is not None:
        device = db.get(Device, alert.device_id)
        if (
            device is not None
            and device.fire_streak > 0
        ):
            raise HTTPException(
                status_code=409,
                detail="Active FIRE_RISK cannot be resolved before cooldown",
            )
    if alert.is_resolved and alert.resolved_at is not None:
        return ResolveAlertResponse(id=alert.id, resolved_at=alert.resolved_at)

    try:
        alert.is_resolved = True
        alert.status = "RESOLVED"
        alert.resolved_at = utcnow()
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not resolve alert_id=%s", alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alert could not be resolved",
        ) from exc

    return ResolveAlertResponse(id=alert.id, resolved_at=alert.resolved_at)
