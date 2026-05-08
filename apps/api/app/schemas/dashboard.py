from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GroupSummaryItem(BaseModel):
    id: str
    product_name: str
    closes_at: str
    order_count: int
    remaining_qty: Optional[int]


class DashboardSummary(BaseModel):
    active_group_count: int
    total_order_count: int
    estimated_revenue: int
    groups: list[GroupSummaryItem]


class PickingAlertItem(BaseModel):
    id: str
    product_name: str
    order_count: int


class DashboardAlert(BaseModel):
    picking_ready_groups: list[PickingAlertItem]
    cancel_request_count: int


class PeriodBucket(BaseModel):
    """매출 / 주문 통계의 한 구간."""

    order_count: int
    revenue: int


class PeriodStats(BaseModel):
    """오늘 / 이번 주 / 이번 달 — 비교 카드용."""

    today: PeriodBucket
    this_week: PeriodBucket
    this_month: PeriodBucket


class RevenueTrendPoint(BaseModel):
    """일자별 매출 추이 한 점. date는 ISO YYYY-MM-DD 형식."""

    date: str
    order_count: int
    revenue: int


class RegularCustomer(BaseModel):
    """단골 고객 한 명. 주문 횟수 / 총 구매 / 마지막 주문일."""

    user_id: str
    nickname: str
    order_count: int
    total_amount: int
    last_order_at: str
