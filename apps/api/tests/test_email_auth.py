from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.core.auth import ALGORITHM, create_email_token
from app.core.config import settings
from app.main import app


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_valid(self, async_client: AsyncClient):
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            resp = await async_client.post(
                "/api/auth/email/signup",
                json={
                    "email": _unique_email(),
                    "password": "password123",
                    "nickname": "테스트",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "customer"
        assert data["is_new"] is True
        assert data["email_verified"] is False
        assert "moaorder_token" in resp.cookies

    @pytest.mark.asyncio
    async def test_signup_invalid_email(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/signup",
            json={"email": "not-an-email", "password": "password123", "nickname": "테스트"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_weak_password_no_number(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/signup",
            json={"email": _unique_email(), "password": "onlyletters", "nickname": "테스트"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_weak_password_too_short(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/signup",
            json={"email": _unique_email(), "password": "abc1", "nickname": "테스트"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_duplicate_email_returns_409(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "첫번째"},
            )
            resp = await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password456", "nickname": "두번째"},
            )
        assert resp.status_code == 409
        assert "이메일" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_correct_password(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )
        resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "customer"
        assert data["is_new"] is False
        assert "moaorder_token" in resp.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )
        resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "wrongpass9"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_reflects_email_verified_false(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )
        resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        assert resp.json()["email_verified"] is False


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_verify_with_valid_token(self, async_client: AsyncClient):
        email = _unique_email()
        captured_token: list[str] = []

        def capture(to: str, token: str, nickname: str) -> str:
            captured_token.append(token)
            return "mock-id"

        with patch("app.api.email_auth.send_verification_email", side_effect=capture):
            signup_resp = await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )
        assert signup_resp.status_code == 200
        assert len(captured_token) == 1

        resp = await async_client.post(
            "/api/auth/email/verify-email",
            json={"token": captured_token[0]},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Login now shows email_verified=True
        login_resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        assert login_resp.json()["email_verified"] is True

    @pytest.mark.asyncio
    async def test_verify_with_expired_token_returns_400(self, async_client: AsyncClient):
        user_id = uuid.uuid4()
        payload = {
            "sub": str(user_id),
            "email": "x@example.com",
            "purpose": "verify",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
        resp = await async_client.post(
            "/api/auth/email/verify-email",
            json={"token": expired_token},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_with_wrong_purpose_returns_400(self, async_client: AsyncClient):
        user_id = uuid.uuid4()
        token = create_email_token(user_id, "x@example.com", "reset", 1)
        resp = await async_client.post(
            "/api/auth/email/verify-email",
            json={"token": token},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_forgot_password_always_returns_200(self, async_client: AsyncClient):
        # Non-existent email
        resp = await async_client.post(
            "/api/auth/email/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user_sends_email(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )

        with patch("app.api.email_auth.send_password_reset_email", return_value="mock-id") as mock_send:
            resp = await async_client.post(
                "/api/auth/email/forgot-password",
                json={"email": email},
            )
        assert resp.status_code == 200
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_does_not_send(self, async_client: AsyncClient):
        with patch("app.api.email_auth.send_password_reset_email") as mock_send:
            resp = await async_client.post(
                "/api/auth/email/forgot-password",
                json={"email": "ghost@example.com"},
            )
        assert resp.status_code == 200
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_password_valid_token(self, async_client: AsyncClient):
        email = _unique_email()
        with patch("app.api.email_auth.send_verification_email", return_value="mock-id"):
            signup_resp = await async_client.post(
                "/api/auth/email/signup",
                json={"email": email, "password": "password123", "nickname": "테스트"},
            )
        user_id = signup_resp.json()["user_id"]

        token = create_email_token(uuid.UUID(user_id), email, "reset", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "newpassword456"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Can now login with new password
        login_resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "newpassword456"},
        )
        assert login_resp.status_code == 200

        # Old password rejected
        old_login = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        assert old_login.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_expired_token_returns_400(self, async_client: AsyncClient):
        user_id = uuid.uuid4()
        payload = {
            "sub": str(user_id),
            "email": "x@example.com",
            "purpose": "reset",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": expired_token, "new_password": "newpassword123"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_wrong_purpose_returns_400(self, async_client: AsyncClient):
        user_id = uuid.uuid4()
        token = create_email_token(user_id, "x@example.com", "verify", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "newpassword123"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_weak_password_returns_422(self, async_client: AsyncClient):
        user_id = uuid.uuid4()
        token = create_email_token(user_id, "x@example.com", "reset", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "weakonly"},
        )
        assert resp.status_code == 422
