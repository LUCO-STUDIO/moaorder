from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# --- Helpers ---


def _make_kakao_info() -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}",
        "nickname": "테스트사장",
        "profile_image": None,
    }


def _future_dt(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


async def _create_owner(client: AsyncClient) -> tuple[str, str]:
    kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        login_resp = await client.post(
            "/api/auth/kakao/exchange",
            json={"code": "test_auth_code"},
        )
    token = login_resp.cookies["moaorder_token"]

    onboard_resp = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": "테스트매장",
            "owner_name": "테스트사장",
            "contact": "010-1234-5678",
            "region": "서울",
            "category": "베이커리",
        },
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    data = onboard_resp.json()
    new_token = onboard_resp.cookies.get("moaorder_token", token)
    return new_token, data["store_id"]


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Dashboard Summary ---


class TestDashboardSummary:
    @pytest.mark.asyncio
    async def test_summary_reflects_open_group(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "대시보드 테스트 공구",
                "price": 10000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/dashboard/summary",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_group_count"] >= 1
        assert len(data["groups"]) >= 1
        assert data["groups"][0]["product_name"] == "대시보드 테스트 공구"

    @pytest.mark.asyncio
    async def test_summary_empty_for_new_store(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        resp = await async_client.get(
            "/api/dashboard/summary",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_group_count"] == 0
        assert data["total_order_count"] == 0
        assert data["estimated_revenue"] == 0
        assert data["groups"] == []

    @pytest.mark.asyncio
    async def test_summary_groups_sorted_by_closes_at(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "늦게 마감",
                "price": 5000,
                "closes_at": _future_dt(48),
            },
            cookies={"moaorder_token": token},
        )
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "빨리 마감",
                "price": 5000,
                "closes_at": _future_dt(2),
            },
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/dashboard/summary",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert len(groups) >= 2
        assert groups[0]["product_name"] == "빨리 마감"
        assert groups[1]["product_name"] == "늦게 마감"

    @pytest.mark.asyncio
    async def test_customer_cannot_access_dashboard(self, async_client: AsyncClient):
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
            "/api/dashboard/summary",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 403


# --- Dashboard Alerts ---


class TestDashboardAlerts:
    @pytest.mark.asyncio
    async def test_alerts_show_picking_list_after_close(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "마감 공구",
                "price": 8000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/dashboard/alerts",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["picking_ready_groups"]) >= 1
        names = [g["product_name"] for g in data["picking_ready_groups"]]
        assert "마감 공구" in names

    @pytest.mark.asyncio
    async def test_alerts_empty_for_new_store(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        resp = await async_client.get(
            "/api/dashboard/alerts",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["picking_ready_groups"] == []
        assert data["cancel_request_count"] == 0

    @pytest.mark.asyncio
    async def test_open_group_not_in_picking_alerts(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "진행중 공구",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/dashboard/alerts",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [g["product_name"] for g in data["picking_ready_groups"]]
        assert "진행중 공구" not in names
