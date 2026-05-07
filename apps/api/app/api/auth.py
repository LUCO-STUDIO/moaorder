from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Union

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_kakao_signup_token,
    exchange_kakao_code,
    get_current_user,
    user_owns_any_store,
    verify_kakao_signup_token,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    KakaoCompleteSignupRequest,
    KakaoExchangeRequest,
    KakaoSignupRequiredResponse,
    TokenResponse,
    UserResponse,
)

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


def _is_age_14_plus(birthdate_yyyymmdd: str) -> bool:
    birth = date(
        int(birthdate_yyyymmdd[0:4]),
        int(birthdate_yyyymmdd[4:6]),
        int(birthdate_yyyymmdd[6:8]),
    )
    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return age >= 14


KakaoExchangeResponse = Union[TokenResponse, KakaoSignupRequiredResponse]


@router.post("/kakao/exchange", response_model=KakaoExchangeResponse)
async def kakao_exchange(
    body: KakaoExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> KakaoExchangeResponse:
    """Exchange Kakao OAuth code.

    - Existing user: issue session cookie + return registered status.
    - New user: do NOT create the account yet; return a signup_token so the
      frontend can collect terms / privacy consent and birthdate before the
      user record is persisted (PIPA §15, §22-2).
    """
    kakao_info = await exchange_kakao_code(body.code)
    kakao_id = kakao_info["kakao_id"]

    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    user = result.scalar_one_or_none()

    if user is not None:
        token = create_access_token(user.id, user.role)
        _set_token_cookie(response, token)
        return TokenResponse(user_id=str(user.id), role=user.role)

    signup_token = create_kakao_signup_token(
        kakao_id=kakao_id,
        nickname=kakao_info.get("nickname"),
        profile_image=kakao_info.get("profile_image"),
    )
    return KakaoSignupRequiredResponse(
        signup_token=signup_token,
        nickname=kakao_info.get("nickname"),
        profile_image=kakao_info.get("profile_image"),
    )


@router.post("/kakao/complete-signup", response_model=TokenResponse)
async def kakao_complete_signup(
    body: KakaoCompleteSignupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Finalize a Kakao signup: verify consent + age, then create the user."""
    if not body.agree_terms:
        raise HTTPException(status_code=400, detail="이용약관에 동의해야 합니다")
    if not _is_age_14_plus(body.birthdate):
        raise HTTPException(status_code=400, detail="만 14세 이상만 가입할 수 있어요")

    payload = verify_kakao_signup_token(body.signup_token)
    kakao_id = payload["kakao_id"]

    # Race-safe: another request might have completed signup in the meantime.
    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            kakao_id=kakao_id,
            role="customer",
            nickname=body.name.strip(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user.id, user.role)
    _set_token_cookie(response, token)
    return TokenResponse(user_id=str(user.id), role=user.role)


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
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    is_owner = await user_owns_any_store(current_user.id, db)
    return UserResponse(
        id=str(current_user.id),
        kakao_id=current_user.kakao_id,
        role=current_user.role,
        is_owner=is_owner,
        nickname=current_user.nickname,
        phone=current_user.phone,
        region=current_user.region,
        category=current_user.category,
        email=current_user.email,
        email_verified=current_user.email_verified_at is not None,
    )
