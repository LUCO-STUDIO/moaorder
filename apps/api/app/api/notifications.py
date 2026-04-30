from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

_VISIBLE_STATUSES = ("sent", "pending")


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        type=n.type,
        channel=n.channel,
        status=n.status,
        title=n.title,
        body=n.body,
        payload=n.payload or {},
        read_at=n.read_at.isoformat() if n.read_at else None,
        created_at=n.created_at.isoformat(),
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> NotificationListResponse:
    base_where = [
        Notification.user_id == current_user.id,
        Notification.status.in_(_VISIBLE_STATUSES),
    ]

    count_result = await db.execute(
        select(func.count(Notification.id)).where(*base_where)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Notification)
        .where(*base_where)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(result.scalars().all())

    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.status.in_(_VISIBLE_STATUSES),
            Notification.read_at.is_(None),
        )
    )
    unread_count = unread_result.scalar_one()

    return NotificationListResponse(
        items=[_to_response(n) for n in items],
        total=total,
        page=page,
        limit=limit,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.status.in_(_VISIBLE_STATUSES),
            Notification.read_at.is_(None),
        )
    )
    return UnreadCountResponse(unread_count=result.scalar_one())


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")

    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notif)

    return _to_response(notif)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status.in_(_VISIBLE_STATUSES),
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.commit()
    return UnreadCountResponse(unread_count=0)
