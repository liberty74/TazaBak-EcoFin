"""Atomic points balance and immutable ledger operations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import PointTransaction, User


@dataclass(frozen=True, slots=True)
class PointsResult:
    transaction: PointTransaction
    balance: int
    replayed: bool = False


def _existing_transaction(
    db: Session, transaction_type: str, reference_id: str | None
) -> PointTransaction | None:
    if reference_id is None:
        return None
    return db.scalar(
        select(PointTransaction)
        .where(
            PointTransaction.transaction_type == transaction_type,
            PointTransaction.reference_id == reference_id,
        )
        .limit(1)
    )


def credit_points(
    db: Session,
    user: User,
    amount: int,
    transaction_type: str,
    description: str,
    reference_id: str | None,
) -> PointsResult:
    if amount <= 0:
        raise ValueError("Credit amount must be positive")
    existing = _existing_transaction(db, transaction_type, reference_id)
    if existing is not None:
        return PointsResult(existing, existing.balance_after, replayed=True)

    result = db.execute(
        update(User)
        .where(User.id == user.id)
        .values(points=User.points + amount)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise RuntimeError("User credit update failed")
    db.expire(user, ["points"])
    balance = user.points
    transaction = PointTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=balance,
        transaction_type=transaction_type,
        description=description,
        reference_id=reference_id,
    )
    db.add(transaction)
    db.flush()
    return PointsResult(transaction, balance)


def debit_points(
    db: Session,
    user: User,
    amount: int,
    transaction_type: str,
    description: str,
    reference_id: str | None,
) -> PointsResult | None:
    if amount <= 0:
        raise ValueError("Debit amount must be positive")
    existing = _existing_transaction(db, transaction_type, reference_id)
    if existing is not None:
        return PointsResult(existing, existing.balance_after, replayed=True)

    result = db.execute(
        update(User)
        .where(User.id == user.id, User.points >= amount)
        .values(points=User.points - amount)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return None
    db.expire(user, ["points"])
    balance = user.points
    transaction = PointTransaction(
        user_id=user.id,
        amount=-amount,
        balance_after=balance,
        transaction_type=transaction_type,
        description=description,
        reference_id=reference_id,
    )
    db.add(transaction)
    db.flush()
    return PointsResult(transaction, balance)

