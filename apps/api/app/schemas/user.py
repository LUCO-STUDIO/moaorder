from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    region: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
