from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.order import Order


# --- Helpers ---


def _make_kakao_info(suffix: str = "") -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}{suffix}",
        "nickname": f"테스트유저{suffix}",
        "profile_image": None,
    }


def _future_dt(hours: int = 48) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_dt(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


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


async def _create_owner(
    client: AsyncClient,
    group_type: str = "reservation",
    min_quantity: int | None = None,
    closes_at: str | None = None,
) -> tuple[str, str, str]:
    from tests.conftest import kakao_login

    token = await kakao_login(client)

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

    group_body: dict = {
        "product_name": "테스트 쿠키",
        "price": 5000,
        "type": group_type,
        "closes_at": closes_at or _future_dt(),
        "max_quantity": 20,
    }
    if group_type == "group_buy" and min_quantity is not None:
        group_body["min_quantity"] = min_quantity

    group_resp = await client.post(
        "/api/groups",
        json=group_body,
        cookies={"moaorder_token": new_token},
    )
    assert group_resp.status_code == 201
    group_id = group_resp.json()["id"]
    return new_token, store_id, group_id


async def _create_customer(client: AsyncClient) -> str:
    from tests.conftest import kakao_login

    token = await kakao_login(client)

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
        return_value={
            "paymentId": payment_id,
            "status": "PAID",
            "amount": {"total": amount},
        },
    ):
        webhook_resp = await client.post(
            "/api/webhooks/portone",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-portone-signature": signature,
            },
        )
    assert webhook_resp.status_code == 200

    orders_resp = await client.get(
        "/api/orders/my",
        cookies={"moaorder_token": customer_token},
    )
    assert orders_resp.status_code == 200
    items = orders_resp.json()["items"]
    matching = [o for o in items if o["group_id"] == group_id]
    assert matching, "주문을 찾을 수 없습니다"
    return matching[0]["id"]


# --- Tests: close_group ---


class TestCloseGroup:
    @pytest.mark.asyncio
    async def test_close_transitions_paid_to_confirmed(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # Close group → all PAID orders should become CONFIRMED
        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        # Verify order status changed to confirmed
        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.status_code == 200
        assert order_resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_close_multiple_paid_orders_all_become_confirmed(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        c1 = await _create_customer(async_client)
        c2 = await _create_customer(async_client)
        order_id1 = await _place_order(async_client, group_id, c1, quantity=1)
        order_id2 = await _place_order(async_client, group_id, c2, quantity=3)

        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200

        for order_id, customer_token in [(order_id1, c1), (order_id2, c2)]:
            order_resp = await async_client.get(
                f"/api/orders/{order_id}",
                cookies={"moaorder_token": customer_token},
            )
            assert order_resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_close_group_buy_min_qty_met_succeeds(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(
            async_client, group_type="group_buy", min_quantity=3
        )
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=5)

        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_close_group_buy_min_qty_not_met_cancels_all(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(
            async_client, group_type="group_buy", min_quantity=10
        )
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token, quantity=2)

        with patch(
            "app.services.refund.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund_123",
        ):
            resp = await async_client.post(
                f"/api/groups/{group_id}/close",
                cookies={"moaorder_token": owner_token},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        # All orders should be cancelled
        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_close_already_closed_returns_400(self, async_client: AsyncClient):
        owner_token, _, group_id = await _create_owner(async_client)

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 400


# --- Tests: set_pickup_ready ---


class TestSetPickupReady:
    @pytest.mark.asyncio
    async def test_pickup_ready_transitions_confirmed_to_pickup_ready(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # Close first
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        # Set pickup ready
        resp = await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pickup_ready"

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "pickup_ready"

    @pytest.mark.asyncio
    async def test_pickup_ready_from_open_returns_400(self, async_client: AsyncClient):
        owner_token, _, group_id = await _create_owner(async_client)

        resp = await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 400


# --- Tests: complete_group ---


class TestCompleteGroup:
    @pytest.mark.asyncio
    async def test_complete_unchecked_orders_become_not_picked_up(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # close → pickup_ready
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )

        # Complete without marking any as picked up
        resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "not_picked_up"

    @pytest.mark.asyncio
    async def test_complete_checked_order_stays_picked_up(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # close → pickup_ready
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )

        # Mark this one as picked up
        mark_resp = await async_client.post(
            f"/api/orders/{order_id}/mark-picked-up",
            cookies={"moaorder_token": owner_token},
        )
        assert mark_resp.status_code == 200

        # Complete the group
        resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 200

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "picked_up"

    @pytest.mark.asyncio
    async def test_complete_mixed_checked_unchecked(self, async_client: AsyncClient):
        owner_token, _, group_id = await _create_owner(async_client)
        c1 = await _create_customer(async_client)
        c2 = await _create_customer(async_client)
        order_id1 = await _place_order(async_client, group_id, c1, quantity=1)
        order_id2 = await _place_order(async_client, group_id, c2, quantity=1)

        # close → pickup_ready
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )

        # Mark only order1 as picked up
        await async_client.post(
            f"/api/orders/{order_id1}/mark-picked-up",
            cookies={"moaorder_token": owner_token},
        )

        # Complete the group
        await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )

        r1 = await async_client.get(
            f"/api/orders/{order_id1}", cookies={"moaorder_token": c1}
        )
        r2 = await async_client.get(
            f"/api/orders/{order_id2}", cookies={"moaorder_token": c2}
        )

        assert r1.json()["status"] == "picked_up"
        assert r2.json()["status"] == "not_picked_up"


# --- Tests: approve/reject cancel ---


class TestCancelHandling:
    @pytest.mark.asyncio
    async def test_approve_cancel_refunds_and_cancels_order(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # Close → order becomes confirmed
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        # Customer requests cancel
        req_resp = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={"reason": "마음이 바뀌었어요"},
            cookies={"moaorder_token": customer_token},
        )
        assert req_resp.status_code == 200

        # Owner approves cancel
        with patch(
            "app.api.owner_orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund_abc",
        ):
            approve_resp = await async_client.post(
                f"/api/orders/{order_id}/approve-cancel",
                cookies={"moaorder_token": owner_token},
            )
        assert approve_resp.status_code == 200

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_reject_cancel_clears_request(self, async_client: AsyncClient):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # Close → confirmed
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        # Customer requests cancel
        await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={"reason": "배송지 변경"},
            cookies={"moaorder_token": customer_token},
        )

        # Owner rejects
        reject_resp = await async_client.post(
            f"/api/orders/{order_id}/reject-cancel",
            cookies={"moaorder_token": owner_token},
        )
        assert reject_resp.status_code == 200

        # Order should still be confirmed
        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.json()["status"] == "confirmed"
        assert order_resp.json()["cancel_requested_at"] is None

    @pytest.mark.asyncio
    async def test_approve_cancel_without_request_returns_400(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        order_id = await _place_order(async_client, group_id, customer_token)

        # Close → confirmed (no cancel request)
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        resp = await async_client.post(
            f"/api/orders/{order_id}/approve-cancel",
            cookies={"moaorder_token": owner_token},
        )
        assert resp.status_code == 400


# --- Tests: picking list ---


class TestPickingList:
    @pytest.mark.asyncio
    async def test_picking_list_shows_confirmed_orders(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        await _place_order(async_client, group_id, customer_token, quantity=3)

        # Close group
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        picking_resp = await async_client.get(
            f"/api/groups/{group_id}/picking-list",
            cookies={"moaorder_token": owner_token},
        )
        assert picking_resp.status_code == 200
        data = picking_resp.json()
        assert data["group_id"] == group_id
        assert data["total_quantity"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_owner_orders_list_includes_crm_fields(
        self, async_client: AsyncClient
    ):
        owner_token, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)
        await _place_order(async_client, group_id, customer_token, quantity=2)

        orders_resp = await async_client.get(
            f"/api/groups/{group_id}/orders",
            cookies={"moaorder_token": owner_token},
        )
        assert orders_resp.status_code == 200
        data = orders_resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert "total_order_count" in item
        assert "is_regular" in item
        assert item["total_order_count"] >= 1
        assert item["is_regular"] is False  # 첫 주문이므로 단골 아님
