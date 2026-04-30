from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    exchange_kakao_code,
    get_current_user,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import KakaoExchangeRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _set_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="moaorder_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


@router.post("/kakao/exchange", response_model=TokenResponse)
async def kakao_exchange(
    body: KakaoExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    kakao_info = await exchange_kakao_code(body.code)
    kakao_id = kakao_info["kakao_id"]

    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    user = result.scalar_one_or_none()

    is_new = user is None
    if is_new:
        user = User(
            kakao_id=kakao_id,
            role="customer",
            nickname=kakao_info.get("nickname"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user.id, user.role)
    _set_token_cookie(response, token)

    return TokenResponse(
        user_id=str(user.id),
        role=user.role,
        is_new=is_new,
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(
        key="moaorder_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        kakao_id=current_user.kakao_id,
        role=current_user.role,
        nickname=current_user.nickname,
        phone=current_user.phone,
        region=current_user.region,
        category=current_user.category,
        email=current_user.email,
        email_verified=current_user.email_verified_at is not None,
    )
