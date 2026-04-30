from __future__ import annotations

import uuid
from datetime import datetime, timezone

from nanoid import generate as nanoid_generate
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import Group, GroupPickupSlot
from app.models.inventory import InventoryHold
from app.models.order import Order, OrderAdjustment, OrderEvent
from app.models.store import Store
from app.schemas.common import GroupStatus, GroupType
from app.schemas.group import (
    GroupCreateRequest,
    GroupPublicResponse,
    GroupResponse,
    GroupUpdateRequest,
    PickupSlotResponse,
)

NANOID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
NANOID_SIZE = 12


def _generate_public_id() -> str:
    return nanoid_generate(NANOID_ALPHABET, NANOID_SIZE)


def _slot_response(slot: GroupPickupSlot) -> PickupSlotResponse:
    return PickupSlotResponse(
        id=str(slot.id),
        label=slot.label,
        start_at=slot.start_at.isoformat(),
        end_at=slot.end_at.isoformat(),
        sort_order=slot.sort_order,
    )


def _group_response(group: Group) -> GroupResponse:
    return GroupResponse(
        id=str(group.id),
        public_id=group.public_id,
        store_id=str(group.store_id),
        status=GroupStatus(group.status),
        type=GroupType(group.type),
        product_name=group.product_name,
        price=group.price,
        description=group.description,
        image_url=group.image_url,
        max_quantity=group.max_quantity,
        remaining_qty=group.remaining_qty,
        min_quantity=group.min_quantity,
        closes_at=group.closes_at.isoformat(),
        closed_at=group.closed_at.isoformat() if group.closed_at else None,
        pickup_slots=[_slot_response(s) for s in group.pickup_slots],
        created_at=group.created_at.isoformat(),
        updated_at=group.updated_at.isoformat(),
    )


def _group_public_response(group: Group, store_name: str) -> GroupPublicResponse:
    return GroupPublicResponse(
        group_id=str(group.id),
        public_id=group.public_id,
        store_id=str(group.store_id),
        store_name=store_name,
        status=GroupStatus(group.status),
        type=GroupType(group.type),
        product_name=group.product_name,
        price=group.price,
        description=group.description,
        image_url=group.image_url,
        max_quantity=group.max_quantity,
        remaining_qty=group.remaining_qty,
        min_quantity=group.min_quantity,
        closes_at=group.closes_at.isoformat(),
        closed_at=group.closed_at.isoformat() if group.closed_at else None,
        pickup_slots=[_slot_response(s) for s in group.pickup_slots],
        created_at=group.created_at.isoformat(),
    )


async def create_group(
    store_id: uuid.UUID,
    body: GroupCreateRequest,
    db: AsyncSession,
) -> Group:
    group = Group(
        public_id=_generate_public_id(),
        store_id=store_id,
        status="open",
        type=body.type.value,
        product_name=body.product_name,
        price=body.price,
        description=body.description,
        image_url=body.image_url,
        max_quantity=body.max_quantity,
        remaining_qty=body.max_quantity,
        min_quantity=body.min_quantity if body.type == GroupType.GROUP_BUY else None,
        closes_at=body.closes_at,
    )
    db.add(group)
    await db.flush()

    if body.type == GroupType.PICKUP and body.pickup_slots:
        for i, slot_req in enumerate(body.pickup_slots):
            slot = GroupPickupSlot(
                group_id=group.id,
                label=slot_req.label,
                start_at=slot_req.start_at,
                end_at=slot_req.end_at,
                sort_order=slot_req.sort_order if slot_req.sort_order else i,
            )
            db.add(slot)

    await db.commit()

    result = await db.execute(
        select(Group)
        .where(Group.id == group.id)
        .options(selectinload(Group.pickup_slots))
    )
    return result.scalar_one()


async def get_group_with_ownership(
    group_id: uuid.UUID,
    store_id: uuid.UUID,
    db: AsyncSession,
) -> Group | None:
    result = await db.execute(
        select(Group)
        .where(Group.id == group_id, Group.store_id == store_id)
        .options(selectinload(Group.pickup_slots))
    )
    return result.scalar_one_or_none()


async def update_group(
    group: Group,
    body: GroupUpdateRequest,
    db: AsyncSession,
) -> Group:
    now = datetime.now(timezone.utc)

    if group.status != "open" or group.closes_at <= now:
        raise ValueError("마감된 공구는 수정할 수 없습니다")

    order_count = await _count_orders(group.id, db)

    if body.type is not None and body.type.value != group.type and order_count > 0:
        raise ValueError("주문이 있는 공구의 타입은 변경할 수 없습니다")

    price_changed = body.price is not None and body.price != group.price
    closes_at_changed = body.closes_at is not None and body.closes_at != group.closes_at

    if body.product_name is not None:
        group.product_name = body.product_name
    if body.price is not None:
        group.price = body.price
    if body.description is not None:
        group.description = body.description
    if body.image_url is not None:
        group.image_url = body.image_url
    if body.closes_at is not None:
        group.closes_at = body.closes_at
    if body.type is not None:
        group.type = body.type.value
    if body.min_quantity is not None:
        group.min_quantity = body.min_quantity

    if body.max_quantity is not None:
        if body.max_quantity < order_count:
            raise ValueError(
                f"판매 가능 수량은 현재 주문 수({order_count}) 이상이어야 합니다"
            )
        sold = (group.max_quantity or 0) - (group.remaining_qty or 0)
        group.max_quantity = body.max_quantity
        group.remaining_qty = body.max_quantity - sold

    if body.pickup_slots is not None:
        await _update_pickup_slots(group, body.pickup_slots, db)

    await db.commit()

    result = await db.execute(
        select(Group)
        .where(Group.id == group.id)
        .options(selectinload(Group.pickup_slots))
    )
    return result.scalar_one(), price_changed, closes_at_changed


async def _update_pickup_slots(
    group: Group,
    new_slots: list,
    db: AsyncSession,
) -> None:
    existing_slot_ids = {str(s.id) for s in group.pickup_slots}

    slots_with_orders = set()
    if existing_slot_ids:
        result = await db.execute(
            select(Order.pickup_slot_id)
            .where(
                Order.pickup_slot_id.in_([uuid.UUID(sid) for sid in existing_slot_ids]),
                Order.status != "cancelled",
            )
            .distinct()
        )
        slots_with_orders = {str(row[0]) for row in result.all()}

    for slot in group.pickup_slots:
        if str(slot.id) in slots_with_orders:
            continue
        await db.delete(slot)

    for i, slot_req in enumerate(new_slots):
        slot = GroupPickupSlot(
            group_id=group.id,
            label=slot_req.label,
            start_at=slot_req.start_at,
            end_at=slot_req.end_at,
            sort_order=slot_req.sort_order if slot_req.sort_order else i,
        )
        db.add(slot)


async def delete_group(
    group: Group,
    db: AsyncSession,
) -> None:
    if group.status != "open":
        raise ValueError("진행 중인 공구만 삭제할 수 있습니다")

    order_count = await _count_orders(group.id, db)
    if order_count > 0:
        raise ValueError("주문이 있는 공구는 삭제할 수 없습니다")

    hold_count = await _count_active_holds(group.id, db)
    if hold_count > 0:
        raise ValueError("결제 대기 중인 공구는 삭제할 수 없습니다")

    await db.delete(group)
    await db.commit()


async def close_group(group: Group, db: AsyncSession) -> Group:
    if group.status != "open":
        raise ValueError("진행 중인 공구만 마감할 수 있습니다")

    from app.services.notification import create_notification
    from app.services.refund import process_full_refund

    now = datetime.now(timezone.utc)

    # Get all PAID orders
    result = await db.execute(
        select(Order).where(Order.group_id == group.id, Order.status == "paid")
    )
    paid_orders = list(result.scalars().all())

    # Get store owner id for notifications
    store_result = await db.execute(select(Store).where(Store.id == group.store_id))
    store = store_result.scalar_one()

    # group_buy min_quantity check
    if group.type == "group_buy" and group.min_quantity is not None:
        total_qty = sum(o.current_quantity for o in paid_orders)
        if total_qty < group.min_quantity:
            group.status = "cancelled"
            group.closed_at = now
            group.cancel_reason = (
                f"최소 수량 미달 (목표 {group.min_quantity}개, 실제 {total_qty}개)"
            )

            for order in paid_orders:
                order.status = "cancelled"

                refund_id = None
                refund_status = "pending"
                try:
                    refund_id = await process_full_refund(order)
                    refund_status = "completed"
                except Exception:
                    refund_status = "failed"

                adj = OrderAdjustment(
                    order_id=order.id,
                    type="system_cancel",
                    quantity_before=order.current_quantity,
                    quantity_after=0,
                    refund_amount=order.current_amount,
                    refund_status=refund_status,
                    refund_payment_id=refund_id,
                    reason="최소 수량 미달로 공구 취소",
                    requested_by="system",
                )
                db.add(adj)

                event = OrderEvent(
                    order_id=order.id,
                    event_type="order_cancelled_system",
                    actor_type="system",
                    extra={"reason": "min_quantity_not_met"},
                )
                db.add(event)

                await create_notification(
                    db,
                    user_id=order.user_id,
                    notification_type="order_cancelled_min_qty",
                    title="공구가 취소되었습니다",
                    body="최소 수량 미달로 공구가 취소되었어요. 결제금액이 환불됩니다.",
                    store_id=group.store_id,
                    group_id=group.id,
                    order_id=order.id,
                    payload={"group_id": str(group.id), "order_id": str(order.id)},
                    dedupe_key=f"order_cancelled_min_qty:{order.id}",
                )

            await create_notification(
                db,
                user_id=store.owner_id,
                notification_type="group_cancelled_min_qty",
                title="공구가 취소되었습니다",
                body=f"최소 수량 미달로 '{group.product_name}' 공구가 취소되었습니다.",
                store_id=group.store_id,
                group_id=group.id,
                payload={"group_id": str(group.id)},
                dedupe_key=f"group_cancelled_min_qty:{group.id}",
            )

            await db.commit()
            await db.refresh(group)
            return group

    # Normal close: PAID → CONFIRMED, notify customers
    group.status = "closed"
    group.closed_at = now

    for order in paid_orders:
        order.status = "confirmed"

        event = OrderEvent(
            order_id=order.id,
            event_type="order_confirmed",
            actor_type="system",
            extra={},
        )
        db.add(event)

        await create_notification(
            db,
            user_id=order.user_id,
            notification_type="order_confirmed",
            title="주문이 확정됐어요",
            body=f"'{group.product_name}' 주문이 확정되었습니다. 상품을 준비 중이에요.",
            store_id=group.store_id,
            group_id=group.id,
            order_id=order.id,
            payload={"group_id": str(group.id), "order_id": str(order.id)},
            dedupe_key=f"order_confirmed:{order.id}",
        )

    await create_notification(
        db,
        user_id=store.owner_id,
        notification_type="picking_list_ready",
        title="피킹 리스트가 준비됐어요",
        body=f"'{group.product_name}' 공구가 마감되었습니다. 피킹 리스트를 확인해주세요.",
        store_id=group.store_id,
        group_id=group.id,
        payload={"group_id": str(group.id)},
        dedupe_key=f"picking_list_ready:{group.id}",
    )

    await db.commit()
    await db.refresh(group)
    return group


async def set_pickup_ready(group: Group, db: AsyncSession) -> Group:
    if group.status != "closed":
        raise ValueError("마감된 공구만 수령 가능으로 변경할 수 있습니다")

    from app.services.notification import create_notification

    # CONFIRMED → PICKUP_READY
    result = await db.execute(
        select(Order).where(Order.group_id == group.id, Order.status == "confirmed")
    )
    confirmed_orders = list(result.scalars().all())

    group.status = "pickup_ready"

    for order in confirmed_orders:
        order.status = "pickup_ready"

        event = OrderEvent(
            order_id=order.id,
            event_type="pickup_ready",
            actor_type="system",
            extra={},
        )
        db.add(event)

        await create_notification(
            db,
            user_id=order.user_id,
            notification_type="pickup_ready",
            title="수령 가능해요",
            body="상품을 수령하실 수 있어요. 매장에 방문해주세요.",
            store_id=group.store_id,
            group_id=group.id,
            order_id=order.id,
            payload={"group_id": str(group.id), "order_id": str(order.id)},
            dedupe_key=f"pickup_ready:{order.id}",
        )

    await db.commit()
    await db.refresh(group)
    return group


async def complete_group(group: Group, db: AsyncSession) -> Group:
    if group.status not in ("closed", "pickup_ready"):
        raise ValueError("마감 또는 수령가능 상태의 공구만 완료할 수 있습니다")

    from app.services.notification import create_notification

    group.status = "completed"

    # picked_up orders: already transitioned individually, just notify
    picked_up_result = await db.execute(
        select(Order).where(Order.group_id == group.id, Order.status == "picked_up")
    )
    for order in picked_up_result.scalars().all():
        await create_notification(
            db,
            user_id=order.user_id,
            notification_type="pickup_confirmed",
            title="수령이 확인됐어요",
            body="상품 수령이 완료되었습니다. 감사합니다!",
            store_id=group.store_id,
            group_id=group.id,
            order_id=order.id,
            payload={"group_id": str(group.id), "order_id": str(order.id)},
            dedupe_key=f"pickup_confirmed:{order.id}",
        )

    # pickup_ready + confirmed → not_picked_up (unchecked)
    unchecked_result = await db.execute(
        select(Order).where(
            Order.group_id == group.id,
            Order.status.in_(["pickup_ready", "confirmed"]),
        )
    )
    for order in unchecked_result.scalars().all():
        order.status = "not_picked_up"

        event = OrderEvent(
            order_id=order.id,
            event_type="not_picked_up",
            actor_type="system",
            extra={},
        )
        db.add(event)

    await db.commit()
    await db.refresh(group)
    return group


async def list_my_groups(
    store_id: uuid.UUID,
    status: str | None,
    page: int,
    limit: int,
    db: AsyncSession,
) -> tuple[list[Group], int]:
    query = (
        select(Group)
        .where(Group.store_id == store_id)
        .options(selectinload(Group.pickup_slots))
    )
    count_query = select(func.count()).select_from(Group).where(Group.store_id == store_id)

    if status:
        query = query.where(Group.status == status)
        count_query = count_query.where(Group.status == status)

    query = query.order_by(Group.created_at.desc()).offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    groups = list(result.scalars().unique().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return groups, total


async def get_public_group(
    public_id: str,
    db: AsyncSession,
) -> tuple[Group, str] | None:
    result = await db.execute(
        select(Group, Store.name)
        .join(Store, Group.store_id == Store.id)
        .where(Group.public_id == public_id)
        .options(selectinload(Group.pickup_slots))
    )
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def list_store_public_groups(
    store_id: uuid.UUID,
    status: str | None,
    sort: str,
    db: AsyncSession,
) -> list[tuple[Group, str]]:
    query = (
        select(Group, Store.name)
        .join(Store, Group.store_id == Store.id)
        .where(Group.store_id == store_id)
        .options(selectinload(Group.pickup_slots))
    )

    if status:
        query = query.where(Group.status == status)
    else:
        query = query.where(Group.status == "open")

    if sort == "closes_at":
        query = query.order_by(Group.closes_at.asc())
    else:
        query = query.order_by(Group.created_at.desc())

    result = await db.execute(query)
    return list(result.unique().all())


async def _count_orders(group_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.group_id == group_id, Order.status != "cancelled")
    )
    return result.scalar() or 0


async def _count_active_holds(group_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(InventoryHold)
        .where(
            InventoryHold.group_id == group_id,
            InventoryHold.status == "active",
        )
    )
    return result.scalar() or 0
