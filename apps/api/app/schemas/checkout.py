import uuid
from typing import Optional

from pydantic import BaseModel, Field


class CheckoutPrepareRequest(BaseModel):
    group_id: uuid.UUID
    quantity: int = Field(ge=1)
    pickup_slot_id: Optional[uuid.UUID] = None


class CheckoutPrepareResponse(BaseModel):
    hold_id: str
    payment_id: str
    store_id: str
    amount: int
    order_name: str


class PaymentStatusResponse(BaseModel):
    status: str  # "processing" | "paid"
    order_id: Optional[str] = None
