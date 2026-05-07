from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.core.auth import ALGORITHM, create_access_token, verify_token
from app.core.config import settings
from app.main import app


# --- JWT unit tests ---


class TestJWT:
    def test_create_and_verify_token(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, "customer")
        claims = verify_token(token)
        assert claims["sub"] == str(user_id)
        assert claims["role"] == "customer"

    def test_expired_token_raises(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "customer",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
        with pytest.raises(Exception) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises(self):
        with pytest.raises(Exception) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_token_missing_sub_raises(self):
        payload = {
            "role": "customer",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
        with pytest.raises(Exception) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401


# --- API integration tests ---


def _make_kakao_info(suffix: str = "") -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}{suffix}",
        "nickname": "테스트유저",
        "profile_image": None,
    }


def _adult_birthdate() -> str:
    """Return a YYYYMMDD string for someone clearly over 14."""
    today = date.today()
    return f"{today.year - 30:04d}0101"


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _signup_via_kakao(
    async_client: AsyncClient,
    kakao_info: dict | None = None,
) -> tuple[str, dict]:
    """Run the full Kakao signup flow and return (token, kakao_info)."""
    if kakao_info is None:
        kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        exchange = await async_client.post(
            "/api/auth/kakao/exchange",
            json={"code": "test_auth_code"},
        )
    assert exchange.status_code == 200
    body = exchange.json()
    assert body["status"] == "needs_signup"

    complete = await async_client.post(
        "/api/auth/kakao/complete-signup",
        json={
            "signup_token": body["signup_token"],
            "name": "테스트유저",
            "birthdate": _adult_birthdate(),
            "agree_terms": True,
            "agree_privacy": True,
        },
    )
    assert complete.status_code == 200
    return complete.cookies["moaorder_token"], kakao_info


class TestKakaoExchange:
    @pytest.mark.asyncio
    async def test_new_user_returns_signup_token(self, async_client: AsyncClient):
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            resp = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "needs_signup"
        assert data["signup_token"]
        assert data["nickname"] == kakao_info["nickname"]
        # No session cookie set yet — user not registered.
        assert "moaorder_token" not in resp.cookies

    @pytest.mark.asyncio
    async def test_existing_user_login(self, async_client: AsyncClient):
        # Register first via the full flow.
        token, kakao_info = await _signup_via_kakao(async_client)

        # Second exchange → existing user, immediate login.
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            resp = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["role"] == "customer"
        assert "moaorder_token" in resp.cookies


class TestKakaoCompleteSignup:
    @pytest.mark.asyncio
    async def test_creates_user(self, async_client: AsyncClient):
        token, info = await _signup_via_kakao(async_client)
        # Confirm /me works with the cookie.
        me = await async_client.get(
            "/api/auth/me",
            cookies={"moaorder_token": token},
        )
        assert me.status_code == 200
        assert me.json()["kakao_id"] == info["kakao_id"]
        assert me.json()["nickname"] == "테스트유저"

    @pytest.mark.asyncio
    async def test_rejects_without_terms(self, async_client: AsyncClient):
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            exchange = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        signup_token = exchange.json()["signup_token"]
        resp = await async_client.post(
            "/api/auth/kakao/complete-signup",
            json={
                "signup_token": signup_token,
                "name": "테스트유저",
                "birthdate": _adult_birthdate(),
                "agree_terms": False,
                "agree_privacy": True,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_under_14(self, async_client: AsyncClient):
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            exchange = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        signup_token = exchange.json()["signup_token"]
        today = date.today()
        # 10-year-old
        too_young = f"{today.year - 10:04d}{today.month:02d}{today.day:02d}"
        resp = await async_client.post(
            "/api/auth/kakao/complete-signup",
            json={
                "signup_token": signup_token,
                "name": "테스트유저",
                "birthdate": too_young,
                "agree_terms": True,
                "agree_privacy": False,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_invalid_signup_token(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/auth/kakao/complete-signup",
            json={
                "signup_token": "not.a.real.token",
                "name": "테스트유저",
                "birthdate": _adult_birthdate(),
                "agree_terms": True,
                "agree_privacy": False,
            },
        )
        assert resp.status_code == 400


class TestAuthMe:
    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, async_client: AsyncClient):
        token, info = await _signup_via_kakao(async_client)
        resp = await async_client.get(
            "/api/auth/me",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["kakao_id"] == info["kakao_id"]
        assert data["role"] == "customer"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_token_returns_401(self, async_client: AsyncClient):
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "customer",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
        resp = await async_client.get(
            "/api/auth/me",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 401


class TestRequireOwner:
    @pytest.mark.asyncio
    async def test_customer_cannot_access_owner_endpoints(self, async_client: AsyncClient):
        token, _ = await _signup_via_kakao(async_client)
        resp = await async_client.patch(
            f"/api/stores/{uuid.uuid4()}",
            json={"name": "test"},
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 403


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, async_client: AsyncClient):
        resp = await async_client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
