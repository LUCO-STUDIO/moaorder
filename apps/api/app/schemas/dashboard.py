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
