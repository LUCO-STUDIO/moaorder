from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class KakaoExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    user_id: str
    role: str
    is_new: bool


class UserResponse(BaseModel):
    id: str
    kakao_id: Optional[str] = None
    role: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    email_verified: bool = False
