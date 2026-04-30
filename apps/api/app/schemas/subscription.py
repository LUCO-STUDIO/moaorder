from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionRequest(BaseModel):
    store_id: str = Field(..., min_length=1)


class SubscriptionResponse(BaseModel):
    id: str
    store_id: str
    store_name: str
    store_category: Optional[str] = None
    created_at: str
