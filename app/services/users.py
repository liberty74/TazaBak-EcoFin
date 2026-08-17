"""Shared user lookup helpers for web and hardware workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def find_user(db: Session, reference: str) -> User | None:
    """Resolve either a public numeric username (e.g. ``123``) or DB id."""

    normalized = reference.strip()
    user = db.scalar(select(User).where(User.username == normalized).limit(1))
    if user is not None:
        return user
    if normalized.isdecimal():
        return db.get(User, int(normalized))
    return None

