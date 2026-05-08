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
        "nickname": "테스트유저",
        "profile_image": None,
    }


def _future_dt(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


async def _create_owner(client: AsyncClient, *, region: str = "서울") -> tuple[str, str]:
    from tests.conftest import kakao_login

    token = await kakao_login(client, region=region)

    onboard_resp = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": f"홈테스트매장_{uuid.uuid4().hex[:4]}",
            "owner_name": "사장님",
            "contact": "010-1234-5678",
            "region": region,
            "category": "카페",
        },
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    data = onboard_resp.json()
    new_token = onboard_resp.cookies.get("moaorder_token", token)
    return new_token, data["store_id"]


async def _create_customer(client: AsyncClient, *, region: str = "서울") -> str:
    from tests.conftest import kakao_login

    # The customer must share the owner's region for the region-scoped /feed
    # to surface the owner's groups, since the feed defaults to the caller's
    # current_user.region when no explicit region is passed.
    token = await kakao_login(client, region=region)

    onboard_resp = await client.post(
        "/api/onboarding/customer",
        json={"nickname": "고객님"},
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    new_token = onboard_resp.cookies.get("moaorder_token", token)
    return new_token


def _unique_region() -> str:
    """Per-test region label so /feed results from other tests don't bleed in."""
    return f"테스트동네_{uuid.uuid4().hex[:6]}"


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Home Feed ---


class TestHomeFeed:
    @pytest.mark.asyncio
    async def test_subscribed_store_group_in_feed(self, async_client: AsyncClient):
        owner_token, store_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        # Subscribe customer to store
        sub_resp = await async_client.post(
            "/api/subscriptions",
            json={"store_id": store_id},
            cookies={"moaorder_token": customer_token},
        )
        assert sub_resp.status_code == 201

        # Owner creates a group
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "구독 피드 공구",
                "price": 7000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.get(
            "/api/home/feed",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        names = [item["product_name"] for item in data]
        assert "구독 피드 공구" in names

    @pytest.mark.asyncio
    async def test_unsubscribed_store_group_not_in_subscribed_feed(self, async_client: AsyncClient):
        # /home/feed used to be subscription-only; it is now region-scoped, and
        # the subscription filter lives at /home/feed/subscribed. The test
        # asserts the new endpoint's contract: groups from stores I don't
        # follow must not surface in my "구독 매장" section.
        owner_token, store_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        # No subscription — owner creates a group
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "비구독 공구",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.get(
            "/api/home/feed/subscribed",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [item["product_name"] for item in data]
        assert "비구독 공구" not in names

    @pytest.mark.asyncio
    async def test_closed_group_not_in_feed(self, async_client: AsyncClient):
        owner_token, store_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        await async_client.post(
            "/api/subscriptions",
            json={"store_id": store_id},
            cookies={"moaorder_token": customer_token},
        )

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "마감된 공구",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": owner_token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.get(
            "/api/home/feed",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [item["product_name"] for item in data]
        assert "마감된 공구" not in names

    @pytest.mark.asyncio
    async def test_feed_sorted_by_closes_at(self, async_client: AsyncClient):
        # Pin owner + customer to a unique region so /feed only contains this
        # test's groups. Without isolation, prior tests leak rows into the
        # default "서울" pool and the ordering assertion sees other "빨리 마감"s.
        region = _unique_region()
        owner_token, _ = await _create_owner(async_client, region=region)
        customer_token = await _create_customer(async_client, region=region)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "늦게 마감",
                "price": 5000,
                "closes_at": _future_dt(48),
            },
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "빨리 마감",
                "price": 5000,
                "closes_at": _future_dt(4),
            },
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.get(
            "/api/home/feed",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["product_name"] == "빨리 마감"
        assert data[1]["product_name"] == "늦게 마감"


# --- Home Today Pickup ---


class TestHomeTodayPickup:
    @pytest.mark.asyncio
    async def test_today_pickup_empty_for_new_customer(self, async_client: AsyncClient):
        customer_token = await _create_customer(async_client)

        resp = await async_client.get(
            "/api/home/today-pickup",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# --- Home Active Orders ---


class TestHomeMyOrdersActive:
    @pytest.mark.asyncio
    async def test_active_orders_empty_for_new_customer(self, async_client: AsyncClient):
        customer_token = await _create_customer(async_client)

        resp = await async_client.get(
            "/api/home/my-orders-active",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        assert resp.json() == []
