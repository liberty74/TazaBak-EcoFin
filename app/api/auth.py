"""Registration and sign-in endpoints for residents and volunteers."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, UserProfile
from app.services.passwords import hash_password, verify_password
from app.services.users import find_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """Create a resident or volunteer account; dispatcher accounts are seeded/admin-only."""

    if find_user(db, payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken")

    tier = "Eco-Volunteer" if payload.role == "volunteer" else "Eco-Starter"
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        points=0,
        status_tier=tier,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken") from exc
    db.refresh(user)
    logger.info("Registered account username=%s role=%s", user.username, user.role)
    return user


@router.post("/login", response_model=UserProfile)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> User:
    """Verify local account credentials and return its public profile."""

    user = find_user(db, payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    logger.info("Account login username=%s role=%s", user.username, user.role)
    return user
