from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_owner
from app.core.database import get_db
from app.models.group import Group, GroupPickupSlot
from app.models.order import Order, OrderAdjustment, OrderEvent
from app.models.store import Store, StoreMember
from app.models.user import User
from app.schemas.order import OwnerOrderItem, OwnerOrderListResponse, OwnerRefundRequest
from app.schemas.picking import PickingItem, PickingListResponse, PickingSlotGroup
from app.services.notification import cancel_pending_notifications_for_order, create_notification
from app.services.refund import process_full_refund

router = APIRouter(tags=["owner-orders"])


async def _get_owner_group(
    group_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Group:
    """Verify ownership and return group."""
    store_result = await db.execute(
        select(StoreMember.store_id).where(
            StoreMember.user_id == current_user.id,
            StoreMember.role == "owner",
        )
    )
    row = store_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")
    store_id = row[0]

    group_result = await db.execute(
        select(Group).where(Group.id == group_id, Group.store_id == store_id)
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")
    return group


async def _get_owner_order(
    order_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Order:
    """Verify ownership and return order."""
    store_result = await db.execute(
        select(StoreMember.store_id).where(
            StoreMember.user_id == current_user.id,
            StoreMember.role == "owner",
        )
    )
    row = store_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")
    store_id = row[0]

    order_result = await db.execute(
        select(Order).where(Order.id == order_id, Order.store_id == store_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    return order


@router.get("/groups/{group_id}/orders", response_model=OwnerOrderListResponse)
async def list_group_orders(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> OwnerOrderListResponse:
    await _get_owner_group(group_id, current_user, db)

    # Fetch all non-cancelled orders for this group with user nicknames
    result = await db.execute(
        select(Order, User.nickname)
        .join(User, Order.user_id == User.id)
        .where(Order.group_id == group_id, Order.status != "cancelled")
        .order_by(Order.created_at.asc())
    )
    rows = result.all()

    if not rows:
        return OwnerOrderListResponse(items=[], total=0, pending_cancel_count=0)

    # Collect unique user_ids for CRM-lite queries
    user_ids = list({row[0].user_id for row in rows})
    store_id = rows[0][0].store_id

    # CRM-lite: per-user order stats for this store
    crm_result = await db.execute(
        select(
            Order.user_id,
            func.count(Order.id).label("order_count"),
            func.sum(Order.current_quantity).label("total_qty"),
            func.max(Order.created_at).label("last_order_date"),
        )
        .where(
            Order.store_id == store_id,
            Order.user_id.in_(user_ids),
            Order.status != "cancelled",
        )
        .group_by(Order.user_id)
    )
    crm_data: dict[uuid.UUID, tuple[int, int, datetime]] = {
        row.user_id: (row.order_count, row.total_qty or 0, row.last_order_date)
        for row in crm_result.all()
    }

    # Fetch pickup slot labels
    slot_ids = [row[0].pickup_slot_id for row in rows if row[0].pickup_slot_id]
    slot_labels: dict[uuid.UUID, str] = {}
    if slot_ids:
        slot_result = await db.execute(
            select(GroupPickupSlot).where(GroupPickupSlot.id.in_(slot_ids))
        )
        for slot in slot_result.scalars().all():
            slot_labels[slot.id] = slot.label

    pending_cancel_count = sum(
        1 for row in rows if row[0].cancel_requested_at is not None
    )

    items: list[OwnerOrderItem] = []
    for order, nickname in rows:
        order_count, total_qty, last_order_date = crm_data.get(
            order.user_id, (1, order.current_quantity, order.created_at)
        )
        items.append(
            OwnerOrderItem(
                id=str(order.id),
                user_id=str(order.user_id),
                user_name=nickname or "알 수 없음",
                status=order.status,
                quantity=order.quantity,
                current_quantity=order.current_quantity,
                total_amount=order.total_amount,
                current_amount=order.current_amount,
                pickup_slot_label=slot_labels.get(order.pickup_slot_id) if order.pickup_slot_id else None,
                cancel_requested_at=(
                    order.cancel_requested_at.isoformat() if order.cancel_requested_at else None
                ),
                cancel_request_reason=order.cancel_request_reason,
                created_at=order.created_at.isoformat(),
                total_order_count=order_count,
                total_quantity_ordered=total_qty,
                last_order_date=last_order_date.isoformat(),
                is_regular=order_count >= 5,
            )
        )

    return OwnerOrderListResponse(
        items=items,
        total=len(items),
        pending_cancel_count=pending_cancel_count,
    )


@router.get("/groups/{group_id}/picking-list", response_model=PickingListResponse)
async def get_picking_list(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> PickingListResponse:
    group = await _get_owner_group(group_id, current_user, db)

    result = await db.execute(
        select(Order, User.nickname)
        .join(User, Order.user_id == User.id)
        .where(
            Order.group_id == group_id,
            Order.status.in_(["confirmed", "pickup_ready", "picked_up"]),
        )
        .order_by(Order.created_at.asc())
    )
    rows = result.all()

    # Fetch pickup slot info
    slot_ids = [row[0].pickup_slot_id for row in rows if row[0].pickup_slot_id]
    slots: dict[uuid.UUID, GroupPickupSlot] = {}
    if slot_ids:
        slot_result = await db.execute(
            select(GroupPickupSlot).where(GroupPickupSlot.id.in_(slot_ids))
        )
        for slot in slot_result.scalars().all():
            slots[slot.id] = slot

    total_quantity = sum(row[0].current_quantity for row in rows)

    items: list[PickingItem] = []
    for order, nickname in rows:
        slot = slots.get(order.pickup_slot_id) if order.pickup_slot_id else None
        items.append(
            PickingItem(
                order_id=str(order.id),
                user_name=nickname or "알 수 없음",
                quantity=order.current_quantity,
                pickup_slot_label=slot.label if slot else None,
                pickup_slot_start_at=slot.start_at.isoformat() if slot else None,
                is_picked_up=order.status == "picked_up",
            )
        )

    # Build slot groups for pickup type
    slot_groups: list[PickingSlotGroup] = []
    if group.type == "pickup":
        slot_map: dict[str, list[PickingItem]] = {}
        no_slot_items: list[PickingItem] = []
        for item in items:
            if item.pickup_slot_label:
                slot_map.setdefault(item.pickup_slot_label, []).append(item)
            else:
                no_slot_items.append(item)

        for slot_label, slot_items in slot_map.items():
            start_at = next(
                (i.pickup_slot_start_at for i in slot_items if i.pickup_slot_start_at),
                None,
            )
            slot_groups.append(
                PickingSlotGroup(
                    slot_label=slot_label,
                    slot_start_at=start_at,
                    items=slot_items,
                )
            )
        if no_slot_items:
            slot_groups.append(
                PickingSlotGroup(slot_label="미지정", items=no_slot_items)
            )

    return PickingListResponse(
        group_id=str(group.id),
        product_name=group.product_name,
        total_quantity=total_quantity,
        items=items,
        slot_groups=slot_groups,
    )


@router.post("/orders/{order_id}/approve-cancel", status_code=200)
async def approve_cancel(
    order_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await _get_owner_order(order_id, current_user, db)

    if order.cancel_requested_at is None:
        raise HTTPException(status_code=400, detail="취소 요청이 없는 주문입니다")

    if order.status not in ("confirmed", "pickup_ready"):
        raise HTTPException(status_code=400, detail="취소 가능한 상태가 아닙니다")

    try:
        refund_id = await process_full_refund(order)
        refund_status = "completed"
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    qty_before = order.current_quantity
    order.status = "cancelled"
    order.cancel_requested_at = None
    await cancel_pending_notifications_for_order(db, order.id)

    adj = OrderAdjustment(
        order_id=order.id,
        type="admin_cancel",
        quantity_before=qty_before,
        quantity_after=0,
        refund_amount=order.current_amount,
        refund_status=refund_status,
        refund_payment_id=refund_id,
        reason=order.cancel_request_reason,
        requested_by="customer",
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(adj)

    event = OrderEvent(
        order_id=order.id,
        event_type="cancel_approved",
        actor_id=current_user.id,
        actor_type="owner",
        extra={"refund_amount": order.current_amount},
    )
    db.add(event)

    await create_notification(
        db,
        user_id=order.user_id,
        notification_type="cancel_approved",
        title="취소 요청이 승인되었습니다",
        body="주문 취소가 승인되었어요. 결제금액이 환불됩니다.",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"cancel_approved:{order.id}",
    )

    await db.commit()
    return {"message": "취소 요청이 승인되었습니다"}


@router.post("/orders/{order_id}/refund", status_code=200)
async def owner_refund(
    order_id: uuid.UUID,
    body: OwnerRefundRequest,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Owner-initiated full refund.

    Used when the owner needs to refund without waiting for a customer
    cancel-request — e.g. delivery damage, quality issue, owner cancels
    the group. The customer is notified after the refund completes.
    """
    order = await _get_owner_order(order_id, current_user, db)

    if order.status not in ("confirmed", "pickup_ready"):
        raise HTTPException(status_code=400, detail="환불 가능한 상태가 아닙니다")

    refund_amount = order.current_amount

    try:
        refund_id = await process_full_refund(order, reason=body.reason)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    qty_before = order.current_quantity
    order.status = "cancelled"
    order.cancel_requested_at = None
    await cancel_pending_notifications_for_order(db, order.id)

    adj = OrderAdjustment(
        order_id=order.id,
        type="admin_cancel",
        quantity_before=qty_before,
        quantity_after=0,
        refund_amount=refund_amount,
        refund_status="completed",
        refund_payment_id=refund_id,
        reason=body.reason,
        requested_by="owner",
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(adj)

    event = OrderEvent(
        order_id=order.id,
        event_type="owner_refund",
        actor_id=current_user.id,
        actor_type="owner",
        extra={"refund_amount": refund_amount, "reason": body.reason},
    )
    db.add(event)

    await create_notification(
        db,
        user_id=order.user_id,
        notification_type="owner_refund",
        title="주문이 환불되었습니다",
        body=f"매장에서 주문을 환불 처리했어요. 사유: {body.reason}",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"owner_refund:{order.id}",
    )

    await db.commit()
    return {
        "message": "환불이 완료되었습니다",
        "refund_amount": refund_amount,
        "refund_payment_id": refund_id,
    }


@router.post("/orders/{order_id}/reject-cancel", status_code=200)
async def reject_cancel(
    order_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await _get_owner_order(order_id, current_user, db)

    if order.cancel_requested_at is None:
        raise HTTPException(status_code=400, detail="취소 요청이 없는 주문입니다")

    order.cancel_requested_at = None
    order.cancel_request_reason = None

    event = OrderEvent(
        order_id=order.id,
        event_type="cancel_rejected",
        actor_id=current_user.id,
        actor_type="owner",
        extra={},
    )
    db.add(event)

    await create_notification(
        db,
        user_id=order.user_id,
        notification_type="cancel_rejected",
        title="취소 요청이 거절되었습니다",
        body="주문 취소 요청이 거절되었어요. 궁금한 점은 매장에 문의해주세요.",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"cancel_rejected:{order.id}",
    )

    await db.commit()
    return {"message": "취소 요청이 거절되었습니다"}


@router.post("/orders/{order_id}/mark-picked-up", status_code=200)
async def mark_picked_up(
    order_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await _get_owner_order(order_id, current_user, db)

    if order.status != "pickup_ready":
        raise HTTPException(status_code=400, detail="수령 가능 상태의 주문만 수령 처리할 수 있습니다")

    order.status = "picked_up"

    event = OrderEvent(
        order_id=order.id,
        event_type="picked_up",
        actor_id=current_user.id,
        actor_type="owner",
        extra={},
    )
    db.add(event)

    await create_notification(
        db,
        user_id=order.user_id,
        notification_type="pickup_confirmed",
        title="수령이 확인됐어요",
        body="상품 수령이 확인되었습니다. 감사합니다!",
        store_id=order.store_id,
        group_id=order.group_id,
        order_id=order.id,
        payload={"group_id": str(order.group_id), "order_id": str(order.id)},
        dedupe_key=f"pickup_confirmed:{order.id}",
    )

    await db.commit()
    return {"message": "수령 처리되었습니다"}
