"""Points shop and procedural Eco-NFT minting."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import EcoNFT, PointTransaction, ShopItem, ShopPurchase
from app.schemas import (
    EcoNFTResponse,
    MintNFTRequest,
    MintNFTResponse,
    ShopBuyRequest,
    ShopBuyResponse,
    ShopItemResponse,
)
from app.services.nft import generate_nft_svg
from app.services.points import debit_points
from app.services.users import find_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shop", tags=["shop"])


def _ledger_balance(
    db: Session, transaction_type: str, reference_id: str, fallback: int
) -> int:
    transaction = db.scalar(
        select(PointTransaction).where(
            PointTransaction.transaction_type == transaction_type,
            PointTransaction.reference_id == reference_id,
        )
    )
    return transaction.balance_after if transaction is not None else fallback


@router.get("/items", response_model=list[ShopItemResponse])
def get_shop_items(db: Session = Depends(get_db)) -> list[ShopItem]:
    return list(
        db.scalars(
            select(ShopItem)
            .where(ShopItem.is_active.is_(True))
            .order_by(ShopItem.price_points.asc(), ShopItem.id.asc())
        ).all()
    )


@router.post("/buy", response_model=ShopBuyResponse)
def buy_shop_item(
    payload: ShopBuyRequest,
    db: Session = Depends(get_db),
) -> ShopBuyResponse:
    user = find_user(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "dispatcher":
        raise HTTPException(status_code=403, detail="Dispatcher cannot buy shop items")
    item = db.get(ShopItem, payload.item_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="Active shop item not found")

    existing = db.scalar(
        select(ShopPurchase).where(
            ShopPurchase.idempotency_key == payload.idempotency_key
        )
    )
    if existing is not None:
        if existing.user_id != user.id or existing.item_id != item.id:
            raise HTTPException(status_code=409, detail="Idempotency key conflict")
        return ShopBuyResponse(
            purchase_id=existing.id,
            user_id=user.id,
            item_id=item.id,
            item_title=item.title,
            spent_points=existing.price_points,
            points_balance=_ledger_balance(
                db, "SHOP_PURCHASE", f"purchase:{existing.id}", user.points
            ),
        )

    try:
        purchase = ShopPurchase(
            user_id=user.id,
            item_id=item.id,
            price_points=item.price_points,
            idempotency_key=payload.idempotency_key,
        )
        db.add(purchase)
        db.flush()
        points_result = debit_points(
            db,
            user,
            item.price_points,
            "SHOP_PURCHASE",
            f"Покупка: {item.title}",
            f"purchase:{purchase.id}",
        )
        if points_result is None:
            db.rollback()
            raise HTTPException(status_code=409, detail="Insufficient points")
        db.commit()
        db.refresh(purchase)
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(ShopPurchase).where(
                ShopPurchase.idempotency_key == payload.idempotency_key
            )
        )
        if replay is not None and replay.user_id == user.id and replay.item_id == item.id:
            return ShopBuyResponse(
                purchase_id=replay.id,
                user_id=user.id,
                item_id=item.id,
                item_title=item.title,
                spent_points=replay.price_points,
                points_balance=_ledger_balance(
                    db, "SHOP_PURCHASE", f"purchase:{replay.id}", user.points
                ),
            )
        raise HTTPException(status_code=409, detail="Idempotency key conflict") from exc
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        db.rollback()
        logger.exception("Shop purchase failed user=%s item=%s", user.id, item.id)
        raise HTTPException(
            status_code=500, detail="Purchase could not be completed"
        ) from exc

    logger.info("Shop purchase completed user=%s item=%s", user.id, item.id)
    return ShopBuyResponse(
        purchase_id=purchase.id,
        user_id=user.id,
        item_id=item.id,
        item_title=item.title,
        spent_points=item.price_points,
        points_balance=points_result.balance,
    )


@router.post("/mint-nft", response_model=MintNFTResponse)
def mint_eco_nft(
    payload: MintNFTRequest,
    db: Session = Depends(get_db),
) -> MintNFTResponse:
    """Atomically debit points, persist ownership and generate safe SVG."""

    user = find_user(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "dispatcher":
        raise HTTPException(status_code=403, detail="Dispatcher cannot mint Eco-NFT")

    existing = db.scalar(
        select(EcoNFT).where(
            EcoNFT.mint_idempotency_key == payload.idempotency_key
        )
    )
    if existing is not None:
        if existing.owner_id != user.id or existing.title != payload.title:
            raise HTTPException(status_code=409, detail="Idempotency key conflict")
        return MintNFTResponse(
            price_points=settings.nft_price_points,
            current_balance=_ledger_balance(
                db, "NFT_MINT", f"nft:{existing.token_id}", user.points
            ),
            nft=EcoNFTResponse.model_validate(existing),
        )

    token_id = str(uuid4())
    try:
        nft = EcoNFT(
            owner_id=user.id,
            token_id=token_id,
            mint_idempotency_key=payload.idempotency_key,
            svg_content="<svg xmlns=\"http://www.w3.org/2000/svg\"/>",
            title=payload.title,
        )
        db.add(nft)
        db.flush()
        nft.svg_content = generate_nft_svg(nft.id, token_id, payload.title)

        points_result = debit_points(
            db,
            user,
            settings.nft_price_points,
            "NFT_MINT",
            f"Минт Eco-NFT: {payload.title}",
            f"nft:{token_id}",
        )
        if points_result is None:
            db.rollback()
            raise HTTPException(status_code=409, detail="Insufficient points")

        db.commit()
        db.refresh(nft)
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(EcoNFT).where(
                EcoNFT.mint_idempotency_key == payload.idempotency_key
            )
        )
        if replay is not None and replay.owner_id == user.id and replay.title == payload.title:
            return MintNFTResponse(
                price_points=settings.nft_price_points,
                current_balance=_ledger_balance(
                    db, "NFT_MINT", f"nft:{replay.token_id}", user.points
                ),
                nft=EcoNFTResponse.model_validate(replay),
            )
        raise HTTPException(status_code=409, detail="Idempotency key conflict") from exc
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        db.rollback()
        logger.exception("Eco-NFT mint failed user=%s token=%s", user.id, token_id)
        raise HTTPException(status_code=500, detail="Eco-NFT could not be minted") from exc

    logger.info("Eco-NFT minted user=%s nft=%s token=%s", user.id, nft.id, token_id)
    return MintNFTResponse(
        price_points=settings.nft_price_points,
        current_balance=points_result.balance,
        nft=EcoNFTResponse.model_validate(nft),
    )
