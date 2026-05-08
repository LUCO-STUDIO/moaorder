from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class KakaoExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Returned when the Kakao user is already registered."""

    status: Literal["registered"] = "registered"
    user_id: str
    role: str


class KakaoSignupRequiredResponse(BaseModel):
    """Returned when the Kakao user is new — frontend should collect consent."""

    status: Literal["needs_signup"] = "needs_signup"
    signup_token: str
    nickname: Optional[str] = None
    profile_image: Optional[str] = None


class KakaoCompleteSignupRequest(BaseModel):
    signup_token: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=50)
    birthdate: str = Field(..., description="YYYYMMDD")
    agree_terms: bool
    agree_privacy: bool = False
    region: str = Field(..., min_length=1, max_length=100)

    @field_validator("birthdate")
    @classmethod
    def _validate_birthdate(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("생년월일은 YYYYMMDD 8자리여야 합니다")
        return v


class UserResponse(BaseModel):
    id: str
    kakao_id: Optional[str] = None
    role: str
    is_owner: bool = False
    nickname: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    email_verified: bool = False
