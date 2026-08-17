"""Community chat endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ForumMessage
from app.schemas import ForumMessageCreate, ForumMessageResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/community", tags=["community"])


@router.get("/chat", response_model=list[ForumMessageResponse])
def get_chat_messages(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[ForumMessage]:
    statement = select(ForumMessage)
    if before_id is not None:
        statement = statement.where(ForumMessage.id < before_id)
    messages = list(
        db.scalars(
            statement.order_by(ForumMessage.id.desc()).limit(limit)
        ).all()
    )
    messages.reverse()
    return messages


@router.post(
    "/chat",
    response_model=ForumMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_chat_message(
    payload: ForumMessageCreate,
    db: Session = Depends(get_db),
) -> ForumMessage:
    message = ForumMessage(username=payload.username, text=payload.text)
    try:
        db.add(message)
        db.commit()
        db.refresh(message)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not persist community message")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message could not be sent",
        ) from exc
    return message

