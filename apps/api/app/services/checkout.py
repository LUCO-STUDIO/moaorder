from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.inventory import InventoryHold
from app.models.order import Order, OrderEvent
from app.models.subscription import Subscription
from app.schemas.checkout import CheckoutPrepareResponse

HOLD_TTL_MINUTES = 10


class SoldOutError(Exception):
    pass


class GroupNotAvailableError(Exception):
    pass


async def prepare_checkout(
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    quantity: int,
    pickup_slot_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> CheckoutPrepareResponse:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=HOLD_TTL_MINUTES)

    # Load group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise GroupNotAvailableError("공구를 찾을 수 없습니다")
    if group.status != "open" or group.closes_at <= now:
        raise GroupNotAvailableError("주문할 수 없는 공구입니다")

    # Check for existing active hold (user + group, UNIQUE index enforces single active hold)
    result = await db.execute(
        select(InventoryHold).where(
            InventoryHold.user_id == user_id,
            InventoryHold.group_id == group_id,
            InventoryHold.status == "active",
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.quantity == quantity:
            # Same quantity — just renew TTL
            existing.expires_at = expires_at
            await db.commit()
            await db.refresh(existing)
            return _prepare_response(existing, group)

        # Different quantity — expire old hold, restore qty, create new hold
        old_qty = existing.quantity
        existing.status = "expired"
        await db.flush()

        # Restore old qty (only when group has a finite limit)
        if group.remaining_qty is not None:
            await db.execute(
                update(Group)
                .where(Group.id == group_id)
                .values(remaining_qty=Group.remaining_qty + old_qty)
            )
            await db.flush()

    # Atomically deduct new quantity
    # For unlimited groups (remaining_qty IS NULL) always succeeds;
    # for finite groups only if remaining_qty >= quantity.
    deduct_result = await db.execute(
        update(Group)
        .where(
            Group.id == group_id,
            or_(Group.remaining_qty.is_(None), Group.remaining_qty >= quantity),
        )
        .values(
            remaining_qty=case(
                (Group.remaining_qty.isnot(None), Group.remaining_qty - quantity),
                else_=None,
            )
        )
        .returning(Group.id)
    )
    if deduct_result.fetchone() is None:
        raise SoldOutError("재고가 부족합니다")

    payment_id = str(uuid.uuid4())
    hold = InventoryHold(
        group_id=group_id,
        user_id=user_id,
        quantity=quantity,
        portone_payment_id=payment_id,
        expires_at=expires_at,
        status="active",
    )
    db.add(hold)
    await db.commit()
    await db.refresh(hold)

    # Reload group to get updated remaining_qty / store_id
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one()

    return _prepare_response(hold, group)


def _prepare_response(hold: InventoryHold, group: Group) -> CheckoutPrepareResponse:
    return CheckoutPrepareResponse(
        hold_id=str(hold.id),
        payment_id=hold.portone_payment_id or str(hold.id),
        store_id=str(group.store_id),
        amount=group.price * hold.quantity,
        order_name=group.product_name,
    )


async def confirm_payment(
    payment_id: str,
    portone_status: str,
    portone_amount: int,
    db: AsyncSession,
) -> Order:
    """
    Called from webhook handler after signature + API verification.
    Creates order, converts hold, records event, auto-subscribes.
    Idempotent via UNIQUE constraint on orders.payment_id.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    # Locate hold
    result = await db.execute(
        select(InventoryHold).where(
            InventoryHold.portone_payment_id == payment_id,
        )
    )
    hold = result.scalar_one_or_none()
    if hold is None:
        raise ValueError(f"hold를 찾을 수 없습니다: payment_id={payment_id}")

    # Load group for price/store
    result = await db.execute(select(Group).where(Group.id == hold.group_id))
    group = result.scalar_one()

    expected_amount = group.price * hold.quantity
    if portone_amount != expected_amount:
        raise ValueError(
            f"결제 금액 불일치: expected={expected_amount}, actual={portone_amount}"
        )
    if portone_status != "PAID":
        raise ValueError(f"결제 상태 불일치: {portone_status}")

    # Check for duplicate (idempotency via UNIQUE on payment_id)
    existing_order_result = await db.execute(
        select(Order).where(Order.payment_id == payment_id)
    )
    existing_order = existing_order_result.scalar_one_or_none()
    if existing_order is not None:
        return existing_order

    now = datetime.now(timezone.utc)
    total = group.price * hold.quantity

    order = Order(
        group_id=hold.group_id,
        user_id=hold.user_id,
        store_id=group.store_id,
        status="paid",
        quantity=hold.quantity,
        total_amount=total,
        current_quantity=hold.quantity,
        current_amount=total,
        payment_id=payment_id,
        paid_at=now,
        pickup_slot_id=None,  # pickup_slot stored in hold if needed; extend later
    )
    db.add(order)
    await db.flush()

    # Convert hold
    hold.status = "converted"
    await db.flush()

    # Record event
    event = OrderEvent(
        order_id=order.id,
        event_type="payment_completed",
        actor_type="system",
        extra={"payment_id": payment_id},
    )
    db.add(event)
    await db.flush()

    # Auto-subscribe (첫 주문 시, ON CONFLICT DO NOTHING)
    stmt = (
        pg_insert(Subscription.__table__)
        .values(user_id=hold.user_id, store_id=group.store_id)
        .on_conflict_do_nothing(constraint="uq_subscriptions_user_store")
    )
    await db.execute(stmt)

    await db.commit()
    await db.refresh(order)
    return order
