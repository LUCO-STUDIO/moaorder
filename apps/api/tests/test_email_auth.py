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


async def _signup(
    async_client: AsyncClient,
    email: str | None = None,
    password: str = "password123",
    nickname: str = "테스트",
    code: str = "123456",
):
    """Run the full inline-verification signup flow. Returns (signup_response, email)."""
    if email is None:
        email = _unique_email()
    with (
        patch(
            "app.api.email_auth.generate_email_verification_code", return_value=code
        ),
        patch(
            "app.api.email_auth.send_verification_code_email", return_value="mock-id"
        ),
    ):
        send_resp = await async_client.post(
            "/api/auth/email/send-code",
            json={"email": email},
        )
        assert send_resp.status_code == 200, send_resp.text
        session_token = send_resp.json()["session_token"]

        verify_resp = await async_client.post(
            "/api/auth/email/verify-code",
            json={"session_token": session_token, "code": code},
        )
        assert verify_resp.status_code == 200, verify_resp.text
        verified_email_token = verify_resp.json()["verified_email_token"]

        signup_resp = await async_client.post(
            "/api/auth/email/signup",
            json={
                "verified_email_token": verified_email_token,
                "password": password,
                "nickname": nickname,
            },
        )
    return signup_resp, email


# ---------------------------------------------------------------------------
# Send code
# ---------------------------------------------------------------------------


class TestSendCode:
    @pytest.mark.asyncio
    async def test_send_code_returns_session_token(self, async_client: AsyncClient):
        with patch(
            "app.api.email_auth.send_verification_code_email", return_value="mock-id"
        ):
            resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": _unique_email()},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_token"]
        assert data["expires_in"] == 5 * 60

    @pytest.mark.asyncio
    async def test_send_code_blocks_existing_account(self, async_client: AsyncClient):
        signup_resp, email = await _signup(async_client)
        assert signup_resp.status_code == 200

        with patch(
            "app.api.email_auth.send_verification_code_email", return_value="mock-id"
        ):
            resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": email},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_send_code_invalid_email_format(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/send-code",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Verify code
# ---------------------------------------------------------------------------


class TestVerifyCode:
    @pytest.mark.asyncio
    async def test_verify_code_correct(self, async_client: AsyncClient):
        with (
            patch(
                "app.api.email_auth.generate_email_verification_code",
                return_value="123456",
            ),
            patch(
                "app.api.email_auth.send_verification_code_email",
                return_value="mock-id",
            ),
        ):
            send_resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": _unique_email()},
            )
        session_token = send_resp.json()["session_token"]

        resp = await async_client.post(
            "/api/auth/email/verify-code",
            json={"session_token": session_token, "code": "123456"},
        )
        assert resp.status_code == 200
        assert resp.json()["verified_email_token"]

    @pytest.mark.asyncio
    async def test_verify_code_wrong(self, async_client: AsyncClient):
        with (
            patch(
                "app.api.email_auth.generate_email_verification_code",
                return_value="123456",
            ),
            patch(
                "app.api.email_auth.send_verification_code_email",
                return_value="mock-id",
            ),
        ):
            send_resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": _unique_email()},
            )
        session_token = send_resp.json()["session_token"]

        resp = await async_client.post(
            "/api/auth/email/verify-code",
            json={"session_token": session_token, "code": "654321"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_code_non_numeric_rejected(self, async_client: AsyncClient):
        with (
            patch(
                "app.api.email_auth.generate_email_verification_code",
                return_value="123456",
            ),
            patch(
                "app.api.email_auth.send_verification_code_email",
                return_value="mock-id",
            ),
        ):
            send_resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": _unique_email()},
            )
        session_token = send_resp.json()["session_token"]

        resp = await async_client.post(
            "/api/auth/email/verify-code",
            json={"session_token": session_token, "code": "abcdef"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_valid(self, async_client: AsyncClient):
        resp, _ = await _signup(async_client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "customer"
        assert data["is_new"] is True
        assert data["email_verified"] is True
        assert "moaorder_token" in resp.cookies

    @pytest.mark.asyncio
    async def test_signup_weak_password_no_number(self, async_client: AsyncClient):
        resp, _ = await _signup(async_client, password="onlyletters")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_weak_password_too_short(self, async_client: AsyncClient):
        resp, _ = await _signup(async_client, password="abc1")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_duplicate_email_returns_409(self, async_client: AsyncClient):
        # First signup OK.
        signup_resp, email = await _signup(async_client)
        assert signup_resp.status_code == 200

        # Subsequent /send-code for the same email should be blocked at the
        # send stage; that's the new behavior.
        with patch(
            "app.api.email_auth.send_verification_code_email", return_value="mock-id"
        ):
            resp = await async_client.post(
                "/api/auth/email/send-code",
                json={"email": email},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_signup_rejects_invalid_verified_token(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/signup",
            json={
                "verified_email_token": "not.a.real.token",
                "password": "password123",
                "nickname": "테스트",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_correct_password(self, async_client: AsyncClient):
        _, email = await _signup(async_client)
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
        _, email = await _signup(async_client)
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
    async def test_signed_up_users_are_email_verified(
        self, async_client: AsyncClient
    ):
        _, email = await _signup(async_client)
        resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        # New flow auto-verifies on signup.
        assert resp.json()["email_verified"] is True


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_forgot_password_always_returns_200(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/email/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user_sends_email(
        self, async_client: AsyncClient
    ):
        _, email = await _signup(async_client)
        with patch(
            "app.api.email_auth.send_password_reset_email", return_value="mock-id"
        ) as mock_send:
            resp = await async_client.post(
                "/api/auth/email/forgot-password",
                json={"email": email},
            )
        assert resp.status_code == 200
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_does_not_send(
        self, async_client: AsyncClient
    ):
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
        signup_resp, email = await _signup(async_client)
        user_id = signup_resp.json()["user_id"]

        token = create_email_token(uuid.UUID(user_id), email, "reset", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "newpassword456"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        login_resp = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "newpassword456"},
        )
        assert login_resp.status_code == 200

        old_login = await async_client.post(
            "/api/auth/email/login",
            json={"email": email, "password": "password123"},
        )
        assert old_login.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_expired_token_returns_400(
        self, async_client: AsyncClient
    ):
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
    async def test_reset_password_wrong_purpose_returns_400(
        self, async_client: AsyncClient
    ):
        user_id = uuid.uuid4()
        token = create_email_token(user_id, "x@example.com", "verify", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "newpassword123"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_weak_password_returns_422(
        self, async_client: AsyncClient
    ):
        user_id = uuid.uuid4()
        token = create_email_token(user_id, "x@example.com", "reset", 1)
        resp = await async_client.post(
            "/api/auth/email/reset-password",
            json={"token": token, "new_password": "weakonly"},
        )
        assert resp.status_code == 422
