from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
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
    from tests.conftest import kakao_login

    token = await kakao_login(client)

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
        from tests.conftest import kakao_login

        token = await kakao_login(async_client)

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


# --- Period stats / revenue trend / regulars helpers ---


async def _seed_paid_order(
    *,
    store_id: str,
    user_nickname: str = "단골고객",
    amount: int = 10000,
    quantity: int = 2,
    created_at: datetime | None = None,
    user_id: str | None = None,
) -> str:
    """Insert a 'paid' order directly via the session factory.

    HTTP-only setup can't pin Order.created_at, which the trend / period-stats
    endpoints care about. Returns the user_id so callers can reuse the same
    customer across multiple seeds (regular-customer aggregation).
    """
    from app.core.database import async_session_factory
    from app.models.group import Group
    from app.models.order import Order
    from app.models.user import User

    async with async_session_factory() as db:
        if user_id is None:
            customer = User(
                kakao_id=f"test_{uuid.uuid4().hex[:8]}",
                role="customer",
                nickname=user_nickname,
            )
            db.add(customer)
            await db.flush()
            user_id = str(customer.id)
        else:
            customer_uuid = uuid.UUID(user_id)

        # Always create a fresh group: the same user cannot hold two active
        # orders against the same group (UNIQUE on (group_id, user_id)), and
        # the regulars test seeds two orders for one user.
        group = Group(
            public_id=uuid.uuid4().hex[:12],
            store_id=uuid.UUID(store_id),
            product_name="대시보드 시드 상품",
            price=amount // max(quantity, 1),
            closes_at=datetime.now(timezone.utc) + timedelta(hours=24),
            max_quantity=100,
        )
        db.add(group)
        await db.flush()

        order_kwargs: dict = {
            "group_id": group.id,
            "user_id": uuid.UUID(user_id),
            "store_id": uuid.UUID(store_id),
            "status": "paid",
            "quantity": quantity,
            "total_amount": amount,
            "current_quantity": quantity,
            "current_amount": amount,
            "payment_id": f"pay_{uuid.uuid4().hex}",
            "paid_at": created_at or datetime.now(timezone.utc),
        }
        if created_at is not None:
            order_kwargs["created_at"] = created_at
        order = Order(**order_kwargs)
        db.add(order)
        await db.commit()

    return user_id


# --- Tests: period stats ---


class TestPeriodStats:
    @pytest.mark.asyncio
    async def test_empty_store_returns_zeros(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        resp = await async_client.get(
            "/api/dashboard/period-stats",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        for bucket in ("today", "this_week", "this_month"):
            assert data[bucket] == {"order_count": 0, "revenue": 0}

    @pytest.mark.asyncio
    async def test_today_bucket_includes_recent_order(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)
        await _seed_paid_order(store_id=store_id, amount=15000, quantity=3)

        resp = await async_client.get(
            "/api/dashboard/period-stats",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["today"]["order_count"] == 1
        assert data["today"]["revenue"] == 15000
        # Today is within both this_week and this_month windows.
        assert data["this_week"]["order_count"] == 1
        assert data["this_month"]["order_count"] == 1

    @pytest.mark.asyncio
    async def test_old_order_excluded_from_today_bucket(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)
        # 40 days ago — outside all three buckets.
        long_ago = datetime.now(timezone.utc) - timedelta(days=40)
        await _seed_paid_order(store_id=store_id, amount=9000, created_at=long_ago)

        resp = await async_client.get(
            "/api/dashboard/period-stats",
            cookies={"moaorder_token": token},
        )
        data = resp.json()
        assert data["today"]["order_count"] == 0
        assert data["this_month"]["order_count"] == 0


# --- Tests: revenue trend ---


class TestRevenueTrend:
    @pytest.mark.asyncio
    async def test_default_returns_seven_points(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)
        resp = await async_client.get(
            "/api/dashboard/revenue-trend",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        # Oldest first, newest last; dates strictly increasing.
        dates = [p["date"] for p in data]
        assert dates == sorted(dates)
        for p in data:
            assert p["order_count"] == 0
            assert p["revenue"] == 0

    @pytest.mark.asyncio
    async def test_days_param_controls_length(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)
        resp = await async_client.get(
            "/api/dashboard/revenue-trend?days=14",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 14

    @pytest.mark.asyncio
    async def test_days_out_of_range_rejected(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)
        for invalid in (0, 91):
            resp = await async_client.get(
                f"/api/dashboard/revenue-trend?days={invalid}",
                cookies={"moaorder_token": token},
            )
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_today_revenue_lands_on_last_point(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)
        await _seed_paid_order(store_id=store_id, amount=20000)

        resp = await async_client.get(
            "/api/dashboard/revenue-trend?days=7",
            cookies={"moaorder_token": token},
        )
        data = resp.json()
        # All revenue must land on today's bucket — the trailing point.
        assert data[-1]["order_count"] == 1
        assert data[-1]["revenue"] == 20000


# --- Tests: regular customers ---


class TestRegulars:
    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)
        resp = await async_client.get(
            "/api/dashboard/regulars",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_ordered_by_order_count(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)
        # Customer A: 2 orders. Customer B: 1 order.
        a_id = await _seed_paid_order(store_id=store_id, user_nickname="단골A", amount=5000)
        await _seed_paid_order(store_id=store_id, user_id=a_id, amount=3000)
        await _seed_paid_order(store_id=store_id, user_nickname="신규B", amount=10000)

        resp = await async_client.get(
            "/api/dashboard/regulars",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["nickname"] == "단골A"
        assert data[0]["order_count"] == 2
        assert data[0]["total_amount"] == 8000
        assert data[1]["nickname"] == "신규B"
        assert data[1]["order_count"] == 1

    @pytest.mark.asyncio
    async def test_limit_param_caps_results(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)
        for nickname in ("a", "b", "c"):
            await _seed_paid_order(store_id=store_id, user_nickname=nickname)

        resp = await async_client.get(
            "/api/dashboard/regulars?limit=2",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# --- Tests: owner gating ---


class TestDashboardOwnerGate:
    @pytest.mark.asyncio
    async def test_period_stats_blocks_non_owner(self, async_client: AsyncClient):
        from tests.conftest import kakao_login

        customer_token = await kakao_login(async_client)
        resp = await async_client.get(
            "/api/dashboard/period-stats",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_revenue_trend_blocks_non_owner(self, async_client: AsyncClient):
        from tests.conftest import kakao_login

        customer_token = await kakao_login(async_client)
        resp = await async_client.get(
            "/api/dashboard/revenue-trend",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regulars_blocks_non_owner(self, async_client: AsyncClient):
        from tests.conftest import kakao_login

        customer_token = await kakao_login(async_client)
        resp = await async_client.get(
            "/api/dashboard/regulars",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 403
