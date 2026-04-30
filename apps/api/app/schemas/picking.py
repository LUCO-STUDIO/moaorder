from typing import Optional

from pydantic import BaseModel


class PickingItem(BaseModel):
    order_id: str
    user_name: str
    quantity: int
    pickup_slot_label: Optional[str] = None
    pickup_slot_start_at: Optional[str] = None
    is_picked_up: bool


class PickingSlotGroup(BaseModel):
    slot_label: str
    slot_start_at: Optional[str] = None
    items: list[PickingItem]


class PickingListResponse(BaseModel):
    group_id: str
    product_name: str
    total_quantity: int
    items: list[PickingItem]
    slot_groups: list[PickingSlotGroup]
