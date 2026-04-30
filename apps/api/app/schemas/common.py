from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field


# --- Error ---


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Pagination ---


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int


# --- Enums ---


class UserRole(str, Enum):
    OWNER = "owner"
    CUSTOMER = "customer"


class GroupStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PICKUP_READY = "pickup_ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GroupType(str, Enum):
    RESERVATION = "reservation"
    GROUP_BUY = "group_buy"
    PICKUP = "pickup"


class OrderStatus(str, Enum):
    PAID = "paid"
    CONFIRMED = "confirmed"
    PICKUP_READY = "pickup_ready"
    PICKED_UP = "picked_up"
    NOT_PICKED_UP = "not_picked_up"
    CANCELLED = "cancelled"


class AdjustmentType(str, Enum):
    QUANTITY_REDUCE = "quantity_reduce"
    FULL_CANCEL = "full_cancel"
    ADMIN_CANCEL = "admin_cancel"
    SYSTEM_CANCEL = "system_cancel"


class RefundStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    INAPP = "inapp"
    SMS = "sms"
    EMAIL = "email"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HoldStatus(str, Enum):
    ACTIVE = "active"
    CONVERTED = "converted"
    EXPIRED = "expired"
