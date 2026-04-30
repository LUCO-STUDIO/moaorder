from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import httpx
from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.store import StoreMember
from app.models.user import User

ALGORITHM = "HS256"


# --- JWT ---


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Returns {"sub": user_id_str, "role": role} or raises."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다") from exc
    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or not role:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    return {"sub": sub, "role": role}


# --- Email verification / password-reset tokens ---


def create_email_token(user_id: uuid.UUID, email: str, purpose: str, expires_hours: int) -> str:
    """Create a short-lived signed JWT for email verification or password reset."""
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "sub": str(user_id),
        "email": email,
        "purpose": purpose,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_email_token(token: str, expected_purpose: str) -> dict:
    """Verify an email token and return its claims, or raise 400."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 토큰입니다") from exc
    if payload.get("purpose") != expected_purpose:
        raise HTTPException(status_code=400, detail="올바르지 않은 토큰 용도입니다")
    return payload


# --- Kakao ---


async def exchange_kakao_code(code: str) -> dict:
    """Exchange authorization code for Kakao user info.

    Returns {"kakao_id": str, "nickname": str | None, "profile_image": str | None}.
    """
    import logging

    logger = logging.getLogger("kakao_auth")

    async with httpx.AsyncClient() as client:
        token_data_body = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }
        if settings.KAKAO_CLIENT_SECRET:
            token_data_body["client_secret"] = settings.KAKAO_CLIENT_SECRET

        logger.warning(
            "[kakao] token request: client_id=%s, redirect_uri=%s, has_secret=%s, code=%s...",
            settings.KAKAO_CLIENT_ID,
            settings.KAKAO_REDIRECT_URI,
            bool(settings.KAKAO_CLIENT_SECRET),
            code[:20] if code else "None",
        )

        token_resp = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data=token_data_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            logger.error("[kakao] token exchange failed: %s %s", token_resp.status_code, token_resp.text)
            raise HTTPException(
                status_code=400,
                detail=f"카카오 인증에 실패했습니다: {token_resp.text}",
            )
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        user_resp = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오 사용자 정보를 가져올 수 없습니다")
        user_data = user_resp.json()

    kakao_id = str(user_data["id"])
    properties = user_data.get("properties", {})
    nickname = properties.get("nickname")
    profile_image = properties.get("profile_image")

    return {
        "kakao_id": kakao_id,
        "nickname": nickname,
        "profile_image": profile_image,
    }


# --- Dependencies ---


async def get_current_user(
    request: Request,
    moaorder_token: Annotated[Optional[str], Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = moaorder_token
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")

    claims = verify_token(token)
    user_id = uuid.UUID(claims["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    return user


async def require_auth(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


async def require_owner(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="사장님만 접근할 수 있습니다")
    return current_user


async def verify_store_ownership(
    store_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verify the current user is an owner of the given store."""
    result = await db.execute(
        select(StoreMember).where(
            StoreMember.store_id == store_id,
            StoreMember.user_id == current_user.id,
            StoreMember.role == "owner",
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="해당 매장에 대한 권한이 없습니다")
