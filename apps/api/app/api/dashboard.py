from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
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
    PeriodBucket,
    PeriodStats,
    PickingAlertItem,
    RegularCustomer,
    RevenueTrendPoint,
)

# Korea-local timezone for "today / this week / this month" rollups. The
# dashboard is owner-facing and stores in this product are local businesses,
# so anchoring to KST is what owners expect — using UTC would split a day at
# 09:00 KST, which is mid-morning for them.
_KST = timezone(timedelta(hours=9))

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


def _kst_today_start() -> datetime:
    """Midnight today in KST, returned as a tz-aware UTC datetime so it can
    be compared against Order.created_at (which Postgres stores in UTC)."""
    now_kst = datetime.now(_KST)
    midnight_kst = datetime.combine(now_kst.date(), datetime.min.time(), tzinfo=_KST)
    return midnight_kst.astimezone(timezone.utc)


def _kst_week_start() -> datetime:
    """Midnight of the current week's Monday in KST."""
    now_kst = datetime.now(_KST)
    monday = now_kst.date() - timedelta(days=now_kst.weekday())
    return datetime.combine(monday, datetime.min.time(), tzinfo=_KST).astimezone(timezone.utc)


def _kst_month_start() -> datetime:
    """Midnight of the 1st of this month in KST."""
    now_kst = datetime.now(_KST)
    first = now_kst.date().replace(day=1)
    return datetime.combine(first, datetime.min.time(), tzinfo=_KST).astimezone(timezone.utc)


async def _bucket_for(store_id: uuid.UUID, since: datetime, db: AsyncSession) -> PeriodBucket:
    result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Order.current_amount), 0),
        ).where(
            Order.store_id == store_id,
            Order.status != "cancelled",
            Order.created_at >= since,
        )
    )
    row = result.first()
    return PeriodBucket(order_count=row[0] or 0, revenue=row[1] or 0)


@router.get("/period-stats", response_model=PeriodStats)
async def get_period_stats(
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> PeriodStats:
    """오늘 / 이번 주(월요일~) / 이번 달(1일~) 주문 수 + 매출. KST 기준."""
    store_id = await _get_owner_store_id(current_user, db)
    return PeriodStats(
        today=await _bucket_for(store_id, _kst_today_start(), db),
        this_week=await _bucket_for(store_id, _kst_week_start(), db),
        this_month=await _bucket_for(store_id, _kst_month_start(), db),
    )


@router.get("/revenue-trend", response_model=list[RevenueTrendPoint])
async def get_revenue_trend(
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> list[RevenueTrendPoint]:
    """KST 일별 매출 추이. 누락 일은 0으로 채워서 정확히 `days`개 반환 (오래된 순).

    days는 1~90 범위. 기본 7일.
    """
    store_id = await _get_owner_store_id(current_user, db)

    today_kst = datetime.now(_KST).date()
    start_date = today_kst - timedelta(days=days - 1)
    since_utc = datetime.combine(start_date, datetime.min.time(), tzinfo=_KST).astimezone(timezone.utc)

    # Group rows by KST calendar date. Postgres stores TIMESTAMPTZ in UTC, so
    # we convert at query time before truncating.
    kst_date = func.date(func.timezone("Asia/Seoul", Order.created_at)).label("d")
    result = await db.execute(
        select(
            kst_date,
            func.count().label("n"),
            func.coalesce(func.sum(Order.current_amount), 0).label("sum"),
        )
        .where(
            Order.store_id == store_id,
            Order.status != "cancelled",
            Order.created_at >= since_utc,
        )
        .group_by(kst_date)
    )
    by_date: dict[date, tuple[int, int]] = {
        row.d: (row.n or 0, row.sum or 0) for row in result.all()
    }

    points: list[RevenueTrendPoint] = []
    for offset in range(days):
        d = start_date + timedelta(days=offset)
        n, s = by_date.get(d, (0, 0))
        points.append(
            RevenueTrendPoint(date=d.isoformat(), order_count=n, revenue=s)
        )
    return points


@router.get("/regulars", response_model=list[RegularCustomer])
async def get_regular_customers(
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
) -> list[RegularCustomer]:
    """주문 횟수 기준 상위 단골 고객. 동률은 총 구매액 → 최근 주문 순으로 정렬."""
    store_id = await _get_owner_store_id(current_user, db)

    result = await db.execute(
        select(
            User.id,
            User.nickname,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.current_amount), 0).label("total_amount"),
            func.max(Order.created_at).label("last_order_at"),
        )
        .join(Order, Order.user_id == User.id)
        .where(
            Order.store_id == store_id,
            Order.status != "cancelled",
        )
        .group_by(User.id, User.nickname)
        .order_by(
            func.count(Order.id).desc(),
            func.sum(Order.current_amount).desc(),
            func.max(Order.created_at).desc(),
        )
        .limit(limit)
    )

    return [
        RegularCustomer(
            user_id=str(row.id),
            nickname=row.nickname or "이름 없음",
            order_count=row.order_count,
            total_amount=row.total_amount,
            last_order_at=row.last_order_at.isoformat(),
        )
        for row in result.all()
    ]
