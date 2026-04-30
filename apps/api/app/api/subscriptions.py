from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.store import Store
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionRequest, SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    store_id = uuid.UUID(body.store_id)

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")

    existing = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.store_id == store_id,
        )
    )
    sub = existing.scalar_one_or_none()

    if sub and sub.unsubscribed_at is None:
        raise HTTPException(status_code=409, detail="이미 구독 중인 매장입니다")

    if sub and sub.unsubscribed_at is not None:
        sub.unsubscribed_at = None
        await db.commit()
        await db.refresh(sub)
    else:
        sub = Subscription(
            user_id=current_user.id,
            store_id=store_id,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

    return SubscriptionResponse(
        id=str(sub.id),
        store_id=str(store.id),
        store_name=store.name,
        store_category=store.category,
        created_at=sub.created_at.isoformat(),
    )


@router.delete("/stores/{store_id}", status_code=204)
async def unsubscribe(
    store_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.store_id == store_id,
            Subscription.unsubscribed_at.is_(None),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")

    sub.unsubscribed_at = datetime.now(timezone.utc)
    await db.commit()


@router.get("/my", response_model=list[SubscriptionResponse])
async def get_my_subscriptions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionResponse]:
    result = await db.execute(
        select(Subscription, Store)
        .join(Store, Subscription.store_id == Store.id)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.unsubscribed_at.is_(None),
        )
        .order_by(Subscription.created_at.desc())
    )
    rows = result.all()

    return [
        SubscriptionResponse(
            id=str(sub.id),
            store_id=str(store.id),
            store_name=store.name,
            store_category=store.category,
            created_at=sub.created_at.isoformat(),
        )
        for sub, store in rows
    ]
