from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StoreResponse(BaseModel):
    id: str
    name: str
    region: Optional[str] = None
    category: Optional[str] = None
    contact: Optional[str] = None
    owner_id: str


class StoreUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    contact: Optional[str] = Field(None, max_length=50)
