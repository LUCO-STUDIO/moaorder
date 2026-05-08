from __future__ import annotations

import os
import re
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_email_code_session_token,
    create_email_token,
    create_email_verified_token,
    generate_email_verification_code,
    verify_email_code_session,
    verify_email_token,
    verify_email_verified_token,
)
from app.core.database import get_db
from app.core.password import hash_password, verify_password
from app.models.user import User
from app.services.email import (
    send_password_reset_email,
    send_verification_code_email,
    send_verification_email,
)

_TESTING = os.getenv("TESTING", "").lower() in ("1", "true", "yes")
limiter = Limiter(key_func=get_remote_address, enabled=not _TESTING)
router = APIRouter(prefix="/auth/email", tags=["email-auth"])

COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


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


def _validate_password(password: str) -> None:
    if not _PASSWORD_RE.match(password):
        raise HTTPException(
            status_code=422,
            detail="비밀번호는 8자 이상이며 영문자와 숫자를 모두 포함해야 합니다",
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    verified_email_token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    nickname: str = Field(..., min_length=1, max_length=50)
    region: str = Field(..., min_length=1, max_length=100)


class SendCodeRequest(BaseModel):
    email: EmailStr


class SendCodeResponse(BaseModel):
    session_token: str
    expires_in: int


class VerifyCodeRequest(BaseModel):
    session_token: str = Field(..., min_length=1)
    code: str = Field(..., min_length=6, max_length=6)


class VerifyCodeResponse(BaseModel):
    verified_email_token: str
    expires_in: int


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    exists: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class EmailTokenResponse(BaseModel):
    user_id: str
    role: str
    is_new: bool
    email_verified: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/send-code", response_model=SendCodeResponse)
@limiter.limit("5/hour")
async def send_code(
    body: SendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SendCodeResponse:
    """Send a 6-digit verification code to the email; return a 5-min session JWT."""
    # Block sending to an already-registered (password-set) email so we
    # don't surprise an existing account holder with a code they didn't ask for.
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and user.password_hash is not None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다")

    code = generate_email_verification_code()
    session_token = create_email_code_session_token(body.email, code)
    try:
        send_verification_code_email(body.email, code)
    except Exception:
        # Don't leak email-provider failures, but still return so the test
        # path keeps working. The code is in the JWT-bound session anyway.
        pass
    return SendCodeResponse(session_token=session_token, expires_in=5 * 60)


@router.post("/verify-code", response_model=VerifyCodeResponse)
@limiter.limit("10/hour")
async def verify_code(
    body: VerifyCodeRequest,
    request: Request,
) -> VerifyCodeResponse:
    """Verify the user-entered 6-digit code against the session JWT."""
    if not body.code.isdigit():
        raise HTTPException(status_code=400, detail="인증번호는 숫자 6자리입니다")
    email = verify_email_code_session(body.session_token, body.code)
    return VerifyCodeResponse(
        verified_email_token=create_email_verified_token(email),
        expires_in=15 * 60,
    )


@router.post("/signup", response_model=EmailTokenResponse)
@limiter.limit("3/hour")
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> EmailTokenResponse:
    _validate_password(body.password)

    email = verify_email_verified_token(body.verified_email_token)

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        role="customer",
        region=body.region.strip(),
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    session_token = create_access_token(user.id, user.role)
    _set_token_cookie(response, session_token)

    return EmailTokenResponse(
        user_id=str(user.id),
        role=user.role,
        is_new=True,
        email_verified=True,
    )


@router.post("/check-email", response_model=CheckEmailResponse)
@limiter.limit("20/minute")
async def check_email(
    body: CheckEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CheckEmailResponse:
    """Check whether an email is registered (Laftel-style step-1 validation).

    Note: this intentionally exposes account existence — a UX trade-off vs
    OWASP guidance. Mitigations: rate limited (20/min/IP), only used in
    pre-auth login flow (not password-reset). Use the standard /login endpoint
    for the actual auth (which uses generic error to prevent enumeration via
    that path).
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    return CheckEmailResponse(exists=user is not None and user.password_hash is not None)


@router.post("/login", response_model=EmailTokenResponse)
@limiter.limit("5/15minutes")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> EmailTokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time path: always verify even if user not found
    # Pre-computed bcrypt hash of "dummy_placeholder" — prevents timing attacks
    dummy_hash = "$2b$12$fj3Q4bUH7OCJWTV6I/ZeZOioWJdBDMoTxjVP2rLlTUFeGWoUwXdYq"
    stored_hash = user.password_hash if user else dummy_hash

    password_ok = verify_password(body.password, stored_hash)

    if not user or not user.password_hash or not password_ok:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    token = create_access_token(user.id, user.role)
    _set_token_cookie(response, token)

    return EmailTokenResponse(
        user_id=str(user.id),
        role=user.role,
        is_new=False,
        email_verified=user.email_verified_at is not None,
    )


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    claims = verify_email_token(body.token, "verify")
    user_id = _uuid.UUID(claims["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()

    return {"ok": True}


@router.post("/resend-verification")
async def resend_verification(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resend verification email. Requires authenticated session."""
    from app.core.auth import get_current_user  # noqa: avoid circular at module level
    try:
        user = await get_current_user(request=request, db=db)
    except HTTPException:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")

    if user.email_verified_at is not None:
        return {"ok": True, "message": "이미 인증된 이메일입니다"}

    if not user.email:
        raise HTTPException(status_code=400, detail="이메일 주소가 없습니다")

    try:
        token = create_email_token(user.id, user.email, "verify", 24)
        send_verification_email(user.email, token, user.nickname or "")
    except Exception:
        pass

    return {"ok": True}


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Always return 200 — don't leak whether email exists
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and user.password_hash:
        try:
            token = create_email_token(user.id, user.email, "reset", 1)
            send_password_reset_email(user.email, token, user.nickname or "")
        except Exception:
            pass

    return {"ok": True}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    _validate_password(body.new_password)

    claims = verify_email_token(body.token, "reset")
    user_id = _uuid.UUID(claims["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"ok": True}
