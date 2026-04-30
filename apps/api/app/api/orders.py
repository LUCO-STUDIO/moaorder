from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.group import Group, GroupPickupSlot
from app.models.order import Order, OrderAdjustment, OrderEvent
from app.models.store import Store
from app.models.user import User
from app.schemas.order import (
    CancelRequestBody,
    OrderDetailResponse,
    OrderEventResponse,
    OrderListResponse,
    OrderSummaryItem,
    PickupSlotInfo,
    ReduceRequest,
)
from app.services.notification import cancel_pending_notifications_for_order, create_notification
from app.services.refund import process_full_refund, process_partial_refund

router = APIRouter(tags=["orders"])

_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "paid": ("주문완료", "마감 전까지 수정할 수 있어요"),
    "confirmed": ("주문 확정", "상품 준비 중이에요"),
    "pickup_ready": ("수령 가능", "매장에서 수령해주세요"),
    "picked_up": ("수령 완료", ""),
    "not_picked_up": ("미수령", "매장에 문의해주세요"),
    "cancelled": ("취소됨", ""),
}

_ACTIVE_STATUSES = ["paid", "confirmed", "pickup_ready"]
_DONE_STATUSES = ["picked_up", "not_picked_up", "cancelled"]


@router.get("/orders/my", response_model=OrderListResponse)
async def list_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    tab: str = Query("active"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> OrderListResponse:
    statuses = _ACTIVE_STATUSES if tab == "active" else _DONE_STATUSES

    count_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == current_user.id,
            Order.status.in_(statuses),
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Order, Group.product_name, Group.closes_at, Group.status, Store.name)
        .join(Group, Order.group_id == Group.id)
        .join(Store, Order.store_id == Store.id)
        .where(
            Order.user_id == current_user.id,
            Order.status.in_(statuses),
        )
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items: list[OrderSummaryItem] = []
    for order, product_name, closes_at, group_status, store_name in result.all():
        label, sub = _STATUS_LABELS.get(order.status, (order.status, ""))
        items.append(
            OrderSummaryItem(
                id=str(order.id),
                group_id=str(order.group_id),
                store_id=str(order.store_id),
                status=order.status,
                status_label=label,
                status_sub=sub,
                product_name=product_name,
                store_name=store_name,
                quantity=order.quantity,
                current_quantity=order.current_quantity,
                total_amount=order.total_amount,
                current_amount=order.current_amount,
                group_closes_at=closes_at.isoformat(),
                group_status=group_status,
                created_at=order.created_at.isoformat(),
            )
        )

    return OrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    result = await db.execute(
        select(Order, Group.product_name, Group.closes_at, Group.status, Store.name)
        .join(Group, Order.group_id == Group.id)
        .join(Store, Order.store_id == Store.id)
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")

    order, product_name, closes_at, group_status, store_name = row
    label, sub = _STATUS_LABELS.get(order.status, (order.status, ""))

    slot_info: Optional[PickupSlotInfo] = None
    if order.pickup_slot_id:
        slot_result = await db.execute(
            select(GroupPickupSlot).where(GroupPickupSlot.id == order.pickup_slot_id)
        )
        slot = slot_result.scalar_one_or_none()
        if slot:
            slot_info = PickupSlotInfo(
                id=str(slot.id),
                label=slot.label,
                start_at=slot.start_at.isoformat(),
                end_at=slot.end_at.isoformat(),
            )

    events = [
        OrderEventResponse(
            id=str(e.id),
            event_type=e.event_type,
            actor_type=e.actor_type,
            metadata=e.extra,
            created_at=e.created_at.isoformat(),
        )
        for e in sorted(order.events, key=lambda x: x.created_at)
    ]

    return OrderDetailResponse(
        id=str(order.id),
        group_id=str(order.group_id),
        store_id=str(order.store_id),
        status=order.status,
        status_label=label,
        status_sub=sub,
        product_name=product_name,
        store_name=store_name,
        quantity=order.quantity,
        total_amount=order.total_amount,
        current_quantity=order.current_quantity,
        current_amount=order.current_amount,
        payment_id=order.payment_id,
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        pickup_slot=slot_info,
        cancel_requested_at=(
            order.cancel_requested_at.isoformat() if order.cancel_requested_at else None
        ),
        events=events,
        group_closes_at=closes_at.isoformat(),
        group_status=group_status,
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
    )


@router.post("/orders/{order_id}/reduce", status_code=200)
async def reduce_order_quantity(
    order_id: uuid.UUID,
    body: ReduceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")

    group_result = await db.execute(select(Group).where(Group.id == order.group_id))
    group = group_result.scalar_one()

    now = datetime.now(timezone.utc)

    if order.status != "paid":
        raise HTTPException(status_code=400, detail="주문완료 상태에서만 수량을 줄일 수 있습니다")

    if group.closes_at <= now or group.status != "open":
        raise HTTPException(status_code=400, detail="마감 후에는 수량을 줄일 수 없습니다")

    if body.quantity_after <= 0:
        raise HTTPException(status_code=400, detail="줄인 후 수량은 1개 이상이어야 합니다")

    if body.quantity_after >= order.current_quantity:
        raise HTTPException(status_code=400, detail="현재 수량보다 적게 입력해주세요")

    qty_before = order.current_quantity
    qty_after = body.quantity_after
    reduced = qty_before - qty_after
    refund_amount = reduced * group.price

    try:
        refund_id = await process_partial_refund(order, refund_amount)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    order.current_quantity = qty_after
    order.current_amount = qty_after * group.price

    if group.remaining_qty is not None:
        await db.execute(
            update(Group)
            .where(Group.id == group.id)
            .values(remaining_qty=Group.remaining_qty + reduced)
        )

    adjustment = OrderAdjustment(
        order_id=order.id,
        type="quantity_reduce",
        quantity_before=qty_before,
        quantity_after=qty_after,
        refund_amount=refund_amount,
        refund_status="completed",
        refund_payment_id=refund_id,
        requested_by="customer",
    )
    db.add(adjustment)

    event = OrderEvent(
        order_id=order.id,
        event_type="quantity_reduced",
        actor_id=current_user.id,
        actor_type="customer",
        extra={
            "quantity_before": qty_before,
            "quantity_after": qty_after,
            "refund_amount": refund_amount,
        },
    )
    db.add(event)

    await db.commit()
    await db.refresh(order)

    return {"message": "수량이 변경되었습니다", "current_quantity": order.current_quantity}


@router.post("/orders/{order_id}/cancel", status_code=200)
async def cancel_order(
    order_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")

    group_result = await db.execute(select(Group).where(Group.id == order.group_id))
    group = group_result.scalar_one()

    now = datetime.now(timezone.utc)

    if order.status != "paid":
        raise HTTPException(status_code=400, detail="주문완료 상태에서만 즉시 취소가 가능합니다")

    if group.closes_at <= now or group.status != "open":
        raise HTTPException(
            status_code=400,
            detail="마감 후에는 즉시 취소가 불가능합니다. 취소 요청을 이용해주세요",
        )

    qty_before = order.current_quantity
    refund_amount = order.current_amount

    try:
        refund_id = await process_full_refund(order)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    order.status = "cancelled"
    await cancel_pending_notifications_for_order(db, order.id)

    if group.remaining_qty is not None:
        await db.execute(
            update(Group)
            .where(Group.id == group.id)
            .values(remaining_qty=Group.remaining_qty + qty_before)
        )

    adjustment = OrderAdjustment(
        order_id=order.id,
        type="full_cancel",
        quantity_before=qty_before,
        quantity_after=0,
        refund_amount=refund_amount,
        refund_status="completed",
        refund_payment_id=refund_id,
        requested_by="customer",
    )
    db.add(adjustment)

    event = OrderEvent(
        order_id=order.id,
        event_type="order_cancelled",
        actor_id=current_user.id,
        actor_type="customer",
        extra={"refund_amount": refund_amount},
    )
    db.add(event)

    store_result = await db.execute(select(Store).where(Store.id == order.store_id))
    store = store_result.scalar_one()
    await create_notification(
        db,
        user_id=store.owner_id,
        notification_type="order_cancelled_pre_close",
        title="주문이 취소되었습니다",
        body="고객이 주문을 취소했습니다",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"order_cancelled_pre_close:{order.id}",
    )

    await db.commit()

    return {"message": "주문이 취소되었습니다"}


@router.post("/orders/{order_id}/cancel-request", status_code=200)
async def request_cancel(
    order_id: uuid.UUID,
    body: CancelRequestBody,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")

    if order.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="주문 확정 상태에서만 취소 요청이 가능합니다",
        )

    if order.cancel_requested_at is not None:
        raise HTTPException(
            status_code=409,
            detail="이미 취소 요청이 접수되어 있습니다",
        )

    now = datetime.now(timezone.utc)
    order.cancel_requested_at = now
    if body.reason:
        order.cancel_request_reason = body.reason

    event = OrderEvent(
        order_id=order.id,
        event_type="cancel_requested",
        actor_id=current_user.id,
        actor_type="customer",
        extra={"reason": body.reason},
    )
    db.add(event)

    store_result = await db.execute(select(Store).where(Store.id == order.store_id))
    store = store_result.scalar_one()
    await create_notification(
        db,
        user_id=store.owner_id,
        notification_type="cancel_request",
        title="취소 요청이 도착했습니다",
        body="고객이 주문 취소를 요청했습니다. 확인 후 처리해주세요",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"cancel_request:{order.id}",
    )

    await db.commit()

    return {"message": "취소 요청이 접수되었습니다"}
