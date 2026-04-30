from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_owner
from app.core.database import get_db
from app.models.group import Group
from app.models.order import Order
from app.models.store import StoreMember
from app.models.user import User
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardSummary,
    GroupSummaryItem,
    PickingAlertItem,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _get_owner_store_id(current_user: User, db: AsyncSession) -> uuid.UUID:
    result = await db.execute(
        select(StoreMember.store_id).where(
            StoreMember.user_id == current_user.id,
            StoreMember.role == "owner",
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")
    return row[0]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    store_id = await _get_owner_store_id(current_user, db)

    active_count_result = await db.execute(
        select(func.count()).where(
            Group.store_id == store_id,
            Group.status == "open",
        )
    )
    active_group_count = active_count_result.scalar() or 0

    order_stats_result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Order.current_amount), 0),
        ).where(
            Order.store_id == store_id,
            Order.status != "cancelled",
        )
    )
    order_stats = order_stats_result.first()
    total_order_count = order_stats[0] or 0
    estimated_revenue = order_stats[1] or 0

    non_cancelled = Order.status != "cancelled"
    groups_result = await db.execute(
        select(
            Group.id,
            Group.product_name,
            Group.closes_at,
            Group.remaining_qty,
            func.count(Order.id).filter(non_cancelled).label("order_count"),
        )
        .outerjoin(Order, Order.group_id == Group.id)
        .where(Group.store_id == store_id, Group.status == "open")
        .group_by(Group.id)
        .order_by(Group.closes_at.asc())
    )

    groups = [
        GroupSummaryItem(
            id=str(row.id),
            product_name=row.product_name,
            closes_at=row.closes_at.isoformat(),
            order_count=row.order_count,
            remaining_qty=row.remaining_qty,
        )
        for row in groups_result.all()
    ]

    return DashboardSummary(
        active_group_count=active_group_count,
        total_order_count=total_order_count,
        estimated_revenue=estimated_revenue,
        groups=groups,
    )


@router.get("/alerts", response_model=DashboardAlert)
async def get_dashboard_alerts(
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> DashboardAlert:
    store_id = await _get_owner_store_id(current_user, db)

    non_cancelled = Order.status != "cancelled"
    closed_groups_result = await db.execute(
        select(
            Group.id,
            Group.product_name,
            Group.closed_at,
            func.count(Order.id).filter(non_cancelled).label("order_count"),
        )
        .outerjoin(Order, Order.group_id == Group.id)
        .where(Group.store_id == store_id, Group.status == "closed")
        .group_by(Group.id, Group.closed_at)
        .order_by(Group.closed_at.desc())
    )

    picking_ready_groups = [
        PickingAlertItem(
            id=str(row.id),
            product_name=row.product_name,
            order_count=row.order_count,
        )
        for row in closed_groups_result.all()
    ]

    cancel_count_result = await db.execute(
        select(func.count()).where(
            Order.store_id == store_id,
            Order.status == "confirmed",
            Order.cancel_requested_at.is_not(None),
        )
    )
    cancel_request_count = cancel_count_result.scalar() or 0

    return DashboardAlert(
        picking_ready_groups=picking_ready_groups,
        cancel_request_count=cancel_request_count,
    )
