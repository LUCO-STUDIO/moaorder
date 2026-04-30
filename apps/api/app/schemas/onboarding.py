from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OwnerOnboardingRequest(BaseModel):
    store_name: str = Field(..., min_length=1, max_length=100)
    owner_name: str = Field(..., min_length=1, max_length=50)
    contact: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)


class CustomerOnboardingRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    region: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
