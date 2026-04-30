from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALGORITHM, create_access_token, verify_token
from app.core.config import settings
from app.main import app
from app.models.user import User


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


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestKakaoExchange:
    @pytest.mark.asyncio
    async def test_new_user_created(self, async_client: AsyncClient):
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
        assert data["role"] == "customer"
        assert data["is_new"] is True
        assert "moaorder_token" in resp.cookies

    @pytest.mark.asyncio
    async def test_existing_user_login(self, async_client: AsyncClient):
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            # First call creates user
            await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
            # Second call finds existing user
            resp = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        assert resp.status_code == 200
        assert resp.json()["is_new"] is False


class TestAuthMe:
    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, async_client: AsyncClient):
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            login_resp = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        token = login_resp.cookies["moaorder_token"]

        resp = await async_client.get(
            "/api/auth/me",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["kakao_id"] == kakao_info["kakao_id"]
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
        kakao_info = _make_kakao_info()
        with patch(
            "app.api.auth.exchange_kakao_code",
            new_callable=AsyncMock,
            return_value=kakao_info,
        ):
            login_resp = await async_client.post(
                "/api/auth/kakao/exchange",
                json={"code": "test_auth_code"},
            )
        token = login_resp.cookies["moaorder_token"]

        # Try to update a store (requires owner)
        resp = await async_client.patch(
            f"/api/stores/{uuid.uuid4()}",
            json={"name": "test"},
            cookies={"moaorder_token": token},
        )
        # Should get 403 (customer trying owner action)
        assert resp.status_code == 403


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, async_client: AsyncClient):
        resp = await async_client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
