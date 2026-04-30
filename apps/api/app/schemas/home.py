from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TodayPickupItem(BaseModel):
    order_id: str
    group_id: str
    product_name: str
    store_name: str
    quantity: int
    group_status: str
    pickup_label: str


class FeedItem(BaseModel):
    public_id: str
    group_id: str
    store_id: str
    store_name: str
    product_name: str
    price: int
    image_url: Optional[str]
    closes_at: str
    remaining_qty: Optional[int]


class ActiveOrderItem(BaseModel):
    order_id: str
    group_id: str
    product_name: str
    store_name: str
    quantity: int
    total_amount: int
    status: str
    status_label: str
    status_sub: str
