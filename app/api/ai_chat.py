"""Role-aware API endpoint for the Gemini-powered eco-assistant Баки."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AIChatRequest, AIChatResponse
from app.services.gemini_bot import GeminiUserContext, gemini_bot
from app.services.users import find_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI assistant"])


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
) -> AIChatResponse:
    """Return a Gemini answer, transparently falling back when unavailable."""

    user_context: GeminiUserContext | None = None
    if payload.user_id is not None:
        user = find_user(db, payload.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user_context = GeminiUserContext(
            username=user.username,
            role=user.role,
            points=user.points,
            status_tier=user.status_tier,
        )

    # Release any DB read state before waiting for the external provider.
    db.rollback()
    reply = await gemini_bot.reply(payload.message, user_context)
    logger.info(
        "AI assistant response provider=%s model=%s role=%s",
        reply.provider,
        reply.model,
        user_context.role if user_context is not None else "anonymous",
    )
    return AIChatResponse(
        response=reply.text,
        provider=reply.provider,
        model=reply.model,
    )
