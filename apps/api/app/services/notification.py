from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.subscription import Subscription


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    notification_type: str,
    title: str,
    body: str | None = None,
    store_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
    scheduled_at: datetime | None = None,
) -> Notification | None:
    """Create a notification, skipping if dedupe_key already exists (non-cancelled)."""
    if dedupe_key is not None:
        result = await db.execute(
            select(Notification).where(
                Notification.dedupe_key == dedupe_key,
                Notification.status != "cancelled",
            )
        )
        if result.scalar_one_or_none() is not None:
            return None

    notif = Notification(
        user_id=user_id,
        store_id=store_id,
        group_id=group_id,
        order_id=order_id,
        type=notification_type,
        title=title,
        body=body,
        payload=payload or {},
        dedupe_key=dedupe_key,
        scheduled_at=scheduled_at or datetime.now(timezone.utc),
    )
    db.add(notif)
    return notif


async def notify_store_subscribers(
    db: AsyncSession,
    *,
    store_id: uuid.UUID,
    group_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    result = await db.execute(
        select(Subscription.user_id).where(
            Subscription.store_id == store_id,
            Subscription.unsubscribed_at.is_(None),
        )
    )
    user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        dedupe_key = f"{notification_type}:{group_id}:{user_id}"
        await create_notification(
            db,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            store_id=store_id,
            group_id=group_id,
            payload=payload or {"group_id": str(group_id)},
            dedupe_key=dedupe_key,
        )

    return len(user_ids)


async def cancel_pending_notifications_for_order(
    db: AsyncSession,
    order_id: uuid.UUID,
) -> int:
    """Cancel all pending/sent (unread) notifications tied to a specific order."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.order_id == order_id,
            Notification.status == "pending",
        )
        .values(status="cancelled")
        .returning(Notification.id)
    )
    return len(result.fetchall())


async def cancel_pending_notifications_for_group(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> int:
    """Cancel all pending notifications tied to a specific group."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.group_id == group_id,
            Notification.status == "pending",
        )
        .values(status="cancelled")
        .returning(Notification.id)
    )
    return len(result.fetchall())


async def schedule_pickup_reminders(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
    store_id: uuid.UUID,
    group_id: uuid.UUID,
    owner_id: uuid.UUID,
    pickup_start: datetime,
    product_name: str,
    quantity: int,
    user_name: str,
) -> None:
    """Schedule pickup reminders 30 minutes before pickup_start."""
    reminder_at = pickup_start - timedelta(minutes=30)
    now = datetime.now(timezone.utc)

    if reminder_at <= now:
        return

    pickup_time = pickup_start.strftime("%H:%M")

    await create_notification(
        db,
        user_id=user_id,
        notification_type="pickup_reminder_customer",
        title="곧 픽업 시간이에요",
        body=f"{pickup_time}에 수령 가능해요. 잊지 마세요!",
        store_id=store_id,
        group_id=group_id,
        order_id=order_id,
        payload={"group_id": str(group_id), "order_id": str(order_id)},
        dedupe_key=f"pickup_reminder_customer:{order_id}",
        scheduled_at=reminder_at,
    )

    await create_notification(
        db,
        user_id=owner_id,
        notification_type="pickup_reminder_owner",
        title="픽업 예정 고객이 있어요",
        body=f"{user_name}님 - {product_name} {quantity}개 ({pickup_time} 픽업 예정)",
        store_id=store_id,
        group_id=group_id,
        order_id=order_id,
        payload={"group_id": str(group_id), "order_id": str(order_id)},
        dedupe_key=f"pickup_reminder_owner:{order_id}",
        scheduled_at=reminder_at,
    )
