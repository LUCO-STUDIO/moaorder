from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import GroupStatus, GroupType


# --- Pickup Slot ---


class PickupSlotRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    start_at: datetime
    end_at: datetime
    sort_order: int = Field(default=0, ge=0)


class PickupSlotResponse(BaseModel):
    id: str
    label: str
    start_at: str
    end_at: str
    sort_order: int


# --- Group Create / Update ---


class GroupCreateRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    price: int = Field(..., gt=0)
    closes_at: datetime
    type: GroupType = GroupType.RESERVATION
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    max_quantity: Optional[int] = Field(None, gt=0)
    min_quantity: Optional[int] = Field(None, gt=0)
    pickup_slots: Optional[list[PickupSlotRequest]] = None


class GroupUpdateRequest(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[int] = Field(None, gt=0)
    closes_at: Optional[datetime] = None
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    max_quantity: Optional[int] = Field(None, gt=0)
    min_quantity: Optional[int] = Field(None, gt=0)
    type: Optional[GroupType] = None
    pickup_slots: Optional[list[PickupSlotRequest]] = None


# --- Group Response ---


class GroupResponse(BaseModel):
    id: str
    public_id: str
    store_id: str
    status: GroupStatus
    type: GroupType
    product_name: str
    price: int
    description: Optional[str] = None
    image_url: Optional[str] = None
    max_quantity: Optional[int] = None
    remaining_qty: Optional[int] = None
    min_quantity: Optional[int] = None
    closes_at: str
    closed_at: Optional[str] = None
    pickup_slots: list[PickupSlotResponse] = []
    created_at: str
    updated_at: str


class GroupPublicResponse(BaseModel):
    group_id: str  # internal UUID — used by checkout/prepare
    public_id: str
    store_id: str
    store_name: str
    status: GroupStatus
    type: GroupType
    product_name: str
    price: int
    description: Optional[str] = None
    image_url: Optional[str] = None
    max_quantity: Optional[int] = None
    remaining_qty: Optional[int] = None
    min_quantity: Optional[int] = None
    closes_at: str
    closed_at: Optional[str] = None
    pickup_slots: list[PickupSlotResponse] = []
    created_at: str


# --- Upload ---


class PresignRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)


class PresignResponse(BaseModel):
    upload_url: str
    public_url: str
