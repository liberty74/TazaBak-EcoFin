"""Profiles, points history, NFT collection and container map endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BinContainer, EcoNFT, PointTransaction, User
from app.schemas import (
    ContainerResponse,
    EcoNFTResponse,
    PointTransactionResponse,
    UserDashboardResponse,
    UserProfile,
)
from app.services.users import find_user


router = APIRouter(tags=["users and map"])


def _require_user(db: Session, user_id: str) -> User:
    user = find_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/api/users/{user_id}", response_model=UserProfile)
def get_user_profile(user_id: str, db: Session = Depends(get_db)) -> User:
    return _require_user(db, user_id)


@router.get(
    "/api/users/{user_id}/transactions",
    response_model=list[PointTransactionResponse],
)
def get_point_transactions(
    user_id: str,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[PointTransaction]:
    user = _require_user(db, user_id)
    statement = select(PointTransaction).where(PointTransaction.user_id == user.id)
    if before_id is not None:
        statement = statement.where(PointTransaction.id < before_id)
    return list(
        db.scalars(statement.order_by(PointTransaction.id.desc()).limit(limit)).all()
    )


@router.get("/api/users/{user_id}/nfts", response_model=list[EcoNFTResponse])
def get_nft_collection(
    user_id: str, db: Session = Depends(get_db)
) -> list[EcoNFT]:
    user = _require_user(db, user_id)
    return list(
        db.scalars(
            select(EcoNFT)
            .where(EcoNFT.owner_id == user.id)
            .order_by(EcoNFT.creation_date.desc(), EcoNFT.id.desc())
        ).all()
    )


@router.get("/api/users/{user_id}/dashboard", response_model=UserDashboardResponse)
def get_user_dashboard(
    user_id: str, db: Session = Depends(get_db)
) -> UserDashboardResponse:
    user = _require_user(db, user_id)
    transactions = list(
        db.scalars(
            select(PointTransaction)
            .where(PointTransaction.user_id == user.id)
            .order_by(PointTransaction.id.desc())
            .limit(50)
        ).all()
    )
    nfts = list(
        db.scalars(
            select(EcoNFT)
            .where(EcoNFT.owner_id == user.id)
            .order_by(EcoNFT.creation_date.desc(), EcoNFT.id.desc())
        ).all()
    )
    return UserDashboardResponse(
        profile=UserProfile.model_validate(user),
        transactions=[PointTransactionResponse.model_validate(row) for row in transactions],
        nfts=[EcoNFTResponse.model_validate(row) for row in nfts],
    )


@router.get("/api/leaderboard", response_model=list[UserProfile])
def get_leaderboard(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_(("user", "volunteer")))
            .order_by(User.points.desc(), User.id.asc())
            .limit(limit)
        ).all()
    )


@router.get("/api/containers", response_model=list[ContainerResponse])
def get_containers(
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> list[ContainerResponse]:
    statement = select(BinContainer).order_by(BinContainer.name.asc())
    if active_only:
        statement = statement.where(BinContainer.is_active.is_(True))
    containers = list(db.scalars(statement).all())
    return [
        ContainerResponse(
            id=container.id,
            device_id=container.device_id,
            name=container.name,
            address=container.address,
            latitude=container.latitude,
            longitude=container.longitude,
            is_active=container.is_active,
            last_fill_level=round(container.last_fill_level, 4),
            fill_percent=round(container.last_fill_level, 4),
        )
        for container in containers
    ]
