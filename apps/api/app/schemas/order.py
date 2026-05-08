from typing import Optional

from pydantic import BaseModel, Field


class OrderResponse(BaseModel):
    id: str
    group_id: str
    store_id: str
    status: str
    quantity: int
    total_amount: int
    current_quantity: int
    current_amount: int
    payment_id: Optional[str] = None
    paid_at: Optional[str] = None
    pickup_slot_id: Optional[str] = None
    created_at: str
    updated_at: str


class OrderEventResponse(BaseModel):
    id: str
    event_type: str
    actor_type: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str


class PickupSlotInfo(BaseModel):
    id: str
    label: str
    start_at: str
    end_at: str


class OrderSummaryItem(BaseModel):
    id: str
    group_id: str
    store_id: str
    status: str
    status_label: str
    status_sub: str
    product_name: str
    store_name: str
    quantity: int
    current_quantity: int
    total_amount: int
    current_amount: int
    group_closes_at: str
    group_status: str
    created_at: str


class OrderDetailResponse(BaseModel):
    id: str
    group_id: str
    store_id: str
    status: str
    status_label: str
    status_sub: str
    product_name: str
    store_name: str
    quantity: int
    total_amount: int
    current_quantity: int
    current_amount: int
    payment_id: Optional[str] = None
    paid_at: Optional[str] = None
    pickup_slot: Optional[PickupSlotInfo] = None
    cancel_requested_at: Optional[str] = None
    events: list[OrderEventResponse]
    group_closes_at: str
    group_status: str
    created_at: str
    updated_at: str


class OrderListResponse(BaseModel):
    items: list[OrderSummaryItem]
    total: int
    page: int
    limit: int


class ReduceRequest(BaseModel):
    quantity_after: int


class CancelRequestBody(BaseModel):
    reason: Optional[str] = None


class OwnerRefundRequest(BaseModel):
    """Owner-initiated full refund. `reason` is required for audit/notification."""

    reason: str = Field(..., min_length=1, max_length=200)


class OwnerOrderItem(BaseModel):
    id: str
    user_id: str
    user_name: str
    status: str
    quantity: int
    current_quantity: int
    total_amount: int
    current_amount: int
    pickup_slot_label: Optional[str] = None
    cancel_requested_at: Optional[str] = None
    cancel_request_reason: Optional[str] = None
    created_at: str
    # CRM-lite
    total_order_count: int
    total_quantity_ordered: int
    last_order_date: str
    is_regular: bool


class OwnerOrderListResponse(BaseModel):
    items: list[OwnerOrderItem]
    total: int
    pending_cancel_count: int
