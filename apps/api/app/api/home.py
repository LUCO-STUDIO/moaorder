from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.group import Group
from app.models.order import Order
from app.models.store import Store
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.home import ActiveOrderItem, FeedItem, TodayPickupItem

router = APIRouter(prefix="/home", tags=["home"])

_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "paid": ("주문완료", "마감 전까지 수정할 수 있어요"),
    "confirmed": ("주문 확정", "상품 준비 중이에요"),
    "pickup_ready": ("수령 가능", "매장에서 수령해주세요"),
    "picked_up": ("수령 완료", ""),
    "not_picked_up": ("미수령", "매장에 문의해주세요"),
    "cancelled": ("취소됨", ""),
}


@router.get("/today-pickup", response_model=list[TodayPickupItem])
async def get_today_pickup(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[TodayPickupItem]:
    result = await db.execute(
        select(Order, Group, Store.name)
        .join(Group, Order.group_id == Group.id)
        .join(Store, Order.store_id == Store.id)
        .where(
            Order.user_id == current_user.id,
            Group.status.in_(["pickup_ready", "closed"]),
            Order.status.in_(["confirmed", "pickup_ready"]),
        )
        .order_by(Group.closes_at.asc())
    )

    items = []
    for order, group, store_name in result.all():
        pickup_label = "수령 가능" if group.status == "pickup_ready" else "준비중"
        items.append(
            TodayPickupItem(
                order_id=str(order.id),
                group_id=str(group.id),
                product_name=group.product_name,
                store_name=store_name,
                quantity=order.current_quantity,
                group_status=group.status,
                pickup_label=pickup_label,
            )
        )
    return items


@router.get("/feed", response_model=list[FeedItem])
async def get_feed(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[FeedItem]:
    result = await db.execute(
        select(Group, Store)
        .join(Store, Group.store_id == Store.id)
        .join(
            Subscription,
            (Subscription.store_id == Group.store_id)
            & (Subscription.user_id == current_user.id),
        )
        .where(
            Subscription.unsubscribed_at.is_(None),
            Group.status == "open",
            (Group.remaining_qty.is_(None)) | (Group.remaining_qty > 0),
        )
        .order_by(Group.closes_at.asc(), Group.created_at.desc())
    )

    return [
        FeedItem(
            public_id=group.public_id,
            group_id=str(group.id),
            store_id=str(group.store_id),
            store_name=store.name,
            product_name=group.product_name,
            price=group.price,
            image_url=group.image_url,
            closes_at=group.closes_at.isoformat(),
            remaining_qty=group.remaining_qty,
        )
        for group, store in result.all()
    ]


@router.get("/my-orders-active", response_model=list[ActiveOrderItem])
async def get_my_orders_active(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ActiveOrderItem]:
    result = await db.execute(
        select(Order, Group.product_name, Store.name)
        .join(Group, Order.group_id == Group.id)
        .join(Store, Order.store_id == Store.id)
        .where(
            Order.user_id == current_user.id,
            Order.status.in_(["paid", "confirmed", "pickup_ready"]),
        )
        .order_by(Order.created_at.desc())
    )

    items = []
    for order, product_name, store_name in result.all():
        label, sub = _STATUS_LABELS.get(order.status, (order.status, ""))
        items.append(
            ActiveOrderItem(
                order_id=str(order.id),
                group_id=str(order.group_id),
                product_name=product_name,
                store_name=store_name,
                quantity=order.current_quantity,
                total_amount=order.current_amount,
                status=order.status,
                status_label=label,
                status_sub=sub,
            )
        )
    return items
