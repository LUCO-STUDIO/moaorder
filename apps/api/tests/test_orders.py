from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.core.config import settings
from app.main import app
from app.models.group import Group
from app.models.order import Order, OrderAdjustment


# --- Helpers (shared with test_checkout pattern) ---


def _make_kakao_info() -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}",
        "nickname": "테스트유저",
        "profile_image": None,
    }


def _future_dt(hours: int = 48) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _make_webhook_signature(payload: bytes) -> str:
    digest = hmac.new(
        settings.PORTONE_API_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"v1={digest}"


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _create_owner(client: AsyncClient) -> tuple[str, str, str]:
    kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        login_resp = await client.post(
            "/api/auth/kakao/exchange", json={"code": "test_code"}
        )
    token = login_resp.cookies["moaorder_token"]

    onboard_resp = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": "테스트매장",
            "owner_name": "사장님",
            "contact": "010-0000-0000",
            "region": "서울",
            "category": "베이커리",
        },
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    new_token = onboard_resp.cookies.get("moaorder_token", token)
    store_id = onboard_resp.json()["store_id"]

    group_resp = await client.post(
        "/api/groups",
        json={
            "product_name": "테스트 쿠키",
            "price": 5000,
            "type": "reservation",
            "closes_at": _future_dt(),
            "max_quantity": 10,
        },
        cookies={"moaorder_token": new_token},
    )
    assert group_resp.status_code == 201
    group_id = group_resp.json()["id"]
    return new_token, store_id, group_id


async def _create_customer(client: AsyncClient) -> str:
    kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        login_resp = await client.post(
            "/api/auth/kakao/exchange", json={"code": "test_code"}
        )
    token = login_resp.cookies["moaorder_token"]

    onboard_resp = await client.post(
        "/api/onboarding/customer",
        json={"nickname": "고객", "region": "서울", "category": "베이커리"},
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    return onboard_resp.cookies.get("moaorder_token", token)


async def _place_order(
    client: AsyncClient,
    group_id: str,
    customer_token: str,
    quantity: int = 2,
) -> str:
    """Prepare + webhook confirm. Returns order_id."""
    prepare_resp = await client.post(
        "/api/checkout/prepare",
        json={"group_id": group_id, "quantity": quantity},
        cookies={"moaorder_token": customer_token},
    )
    assert prepare_resp.status_code == 200
    payment_id = prepare_resp.json()["payment_id"]
    amount = prepare_resp.json()["amount"]

    payload = json.dumps(
        {"type": "Transaction.Paid", "data": {"paymentId": payment_id}}
    ).encode()
    signature = _make_webhook_signature(payload)

    with patch(
        "app.api.webhooks.get_payment",
        new_callable=AsyncMock,
        return_value={"paymentId": payment_id, "status": "PAID", "amount": {"total": amount}},
    ):
        webhook_resp = await client.post(
            "/api/webhooks/portone",
            content=payload,
            headers={"Content-Type": "application/json", "x-portone-signature": signature},
        )
    assert webhook_resp.status_code == 200

    order_resp = await client.get(
        f"/api/orders/by-payment/{payment_id}",
        cookies={"moaorder_token": customer_token},
    )
    assert order_resp.status_code == 200
    return order_resp.json()["order_id"]


# --- Tests ---


class TestListMyOrders:
    @pytest.mark.asyncio
    async def test_returns_active_orders(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        await _place_order(async_client, group_id, customer_token)

        resp = await async_client.get(
            "/api/orders/my",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert item["status"] == "paid"
        assert item["status_label"] == "주문완료"
        assert item["product_name"] == "테스트 쿠키"

    @pytest.mark.asyncio
    async def test_completed_tab_empty_for_new_orders(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        await _place_order(async_client, group_id, customer_token)

        resp = await async_client.get(
            "/api/orders/my?tab=completed",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        # New paid orders don't appear in completed tab
        data = resp.json()
        paid_items = [i for i in data["items"] if i["status"] == "paid"]
        assert len(paid_items) == 0

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get("/api/orders/my")
        assert resp.status_code == 401


class TestGetOrderDetail:
    @pytest.mark.asyncio
    async def test_returns_detail_with_events(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == order_id
        assert data["status"] == "paid"
        assert data["product_name"] == "테스트 쿠키"
        assert len(data["events"]) >= 1
        assert data["events"][0]["event_type"] == "payment_completed"

    @pytest.mark.asyncio
    async def test_other_user_cannot_access(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        other_token = await _create_customer(async_client)
        resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": other_token},
        )
        assert resp.status_code == 404


class TestReduceOrderQuantity:
    @pytest.mark.asyncio
    async def test_reduce_updates_quantity_and_creates_adjustment(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=3)

        with patch(
            "app.api.orders.process_partial_refund",
            new_callable=AsyncMock,
            return_value="refund-id-001",
        ):
            resp = await async_client.post(
                f"/api/orders/{order_id}/reduce",
                json={"quantity_after": 1},
                cookies={"moaorder_token": customer_token},
            )

        assert resp.status_code == 200
        assert resp.json()["current_quantity"] == 1

        # Verify order detail reflects change
        detail_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        data = detail_resp.json()
        assert data["current_quantity"] == 1
        assert data["current_amount"] == 5000  # 1 * 5000

    @pytest.mark.asyncio
    async def test_reduce_restores_remaining_qty(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=3)

        # remaining_qty before reduce: 10 - 3 = 7
        with patch(
            "app.api.orders.process_partial_refund",
            new_callable=AsyncMock,
            return_value="refund-id-002",
        ):
            await async_client.post(
                f"/api/orders/{order_id}/reduce",
                json={"quantity_after": 1},
                cookies={"moaorder_token": customer_token},
            )

        # remaining_qty after reduce: 7 + 2 = 9
        group_result = await db.execute(
            select(Group).where(Group.id == uuid.UUID(group_id))
        )
        group = group_result.scalar_one()
        assert group.remaining_qty == 9

    @pytest.mark.asyncio
    async def test_reduce_after_deadline_returns_error(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        # Force group past deadline
        await db.execute(
            update(Group)
            .where(Group.id == uuid.UUID(group_id))
            .values(closes_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        await db.commit()

        resp = await async_client.post(
            f"/api/orders/{order_id}/reduce",
            json={"quantity_after": 1},
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reduce_quantity_not_less_than_current_returns_error(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        resp = await async_client.post(
            f"/api/orders/{order_id}/reduce",
            json={"quantity_after": 2},  # same as current
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reduce_zero_quantity_returns_error(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        resp = await async_client.post(
            f"/api/orders/{order_id}/reduce",
            json={"quantity_after": 0},
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 400


class TestCancelOrder:
    @pytest.mark.asyncio
    async def test_cancel_sets_status_and_creates_adjustment(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        with patch(
            "app.api.orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-full-001",
        ):
            resp = await async_client.post(
                f"/api/orders/{order_id}/cancel",
                cookies={"moaorder_token": customer_token},
            )

        assert resp.status_code == 200

        detail_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        data = detail_resp.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_restores_remaining_qty(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        # remaining_qty before cancel: 10 - 2 = 8
        with patch(
            "app.api.orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-full-002",
        ):
            await async_client.post(
                f"/api/orders/{order_id}/cancel",
                cookies={"moaorder_token": customer_token},
            )

        # remaining_qty after cancel: 8 + 2 = 10
        group_result = await db.execute(
            select(Group).where(Group.id == uuid.UUID(group_id))
        )
        group = group_result.scalar_one()
        assert group.remaining_qty == 10

    @pytest.mark.asyncio
    async def test_cancel_after_deadline_returns_error(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=1)

        # Force group past deadline
        await db.execute(
            update(Group)
            .where(Group.id == uuid.UUID(group_id))
            .values(closes_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        await db.commit()

        resp = await async_client.post(
            f"/api/orders/{order_id}/cancel",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 400


class TestCancelRequest:
    @pytest.mark.asyncio
    async def test_cancel_request_sets_timestamp_and_notifies_owner(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=1)

        # Set order to confirmed status (simulates post-deadline)
        await db.execute(
            update(Order)
            .where(Order.id == uuid.UUID(order_id))
            .values(status="confirmed")
        )
        await db.commit()

        resp = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={"reason": "단순 변심"},
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200

        # Verify cancel_requested_at is set
        order_result = await db.execute(
            select(Order).where(Order.id == uuid.UUID(order_id))
        )
        order = order_result.scalar_one()
        assert order.cancel_requested_at is not None
        assert order.cancel_request_reason == "단순 변심"

    @pytest.mark.asyncio
    async def test_duplicate_cancel_request_returns_409(
        self, async_client: AsyncClient, db
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=1)

        await db.execute(
            update(Order)
            .where(Order.id == uuid.UUID(order_id))
            .values(status="confirmed")
        )
        await db.commit()

        # First request
        r1 = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={},
            cookies={"moaorder_token": customer_token},
        )
        assert r1.status_code == 200

        # Duplicate
        r2 = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={},
            cookies={"moaorder_token": customer_token},
        )
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_request_on_paid_order_returns_error(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=1)

        # Order is still 'paid' (not confirmed)
        resp = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={},
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 400
