from __future__ import annotations

import asyncio
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


def _make_kakao_info(suffix: str = "") -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}{suffix}",
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
    """Create owner, onboard, return (token, store_id, group_id)."""
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
    """Create customer, onboard, return token."""
    from tests.conftest import kakao_login

    token = await kakao_login(client)

    onboard_resp = await client.post(
        "/api/onboarding/customer",
        json={"nickname": "고객", "region": "서울", "category": "베이커리"},
        cookies={"moaorder_token": token},
    )
    assert onboard_resp.status_code == 200
    return onboard_resp.cookies.get("moaorder_token", token)


# --- Tests ---


class TestCheckoutPrepare:
    @pytest.mark.asyncio
    async def test_prepare_creates_hold_and_returns_payment_id(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 2},
            cookies={"moaorder_token": customer_token},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["hold_id"]
        assert data["payment_id"]
        assert data["amount"] == 10000  # 5000 * 2
        assert data["order_name"] == "테스트 쿠키"

    @pytest.mark.asyncio
    async def test_prepare_same_quantity_renews_hold(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        r1 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
        assert r1.status_code == 200
        hold_id_1 = r1.json()["hold_id"]
        payment_id_1 = r1.json()["payment_id"]

        r2 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
        assert r2.status_code == 200
        # Same hold returned with renewed TTL
        assert r2.json()["hold_id"] == hold_id_1
        assert r2.json()["payment_id"] == payment_id_1

    @pytest.mark.asyncio
    async def test_prepare_different_quantity_replaces_hold(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        r1 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 3},
            cookies={"moaorder_token": customer_token},
        )
        assert r1.status_code == 200
        hold_id_1 = r1.json()["hold_id"]

        r2 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 2},
            cookies={"moaorder_token": customer_token},
        )
        assert r2.status_code == 200
        # New hold with new hold_id
        assert r2.json()["hold_id"] != hold_id_1
        assert r2.json()["amount"] == 10000  # 5000 * 2

    @pytest.mark.asyncio
    async def test_prepare_sold_out_returns_409(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        # Customer 1 takes all 10
        c1 = await _create_customer(async_client)
        r1 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 10},
            cookies={"moaorder_token": c1},
        )
        assert r1.status_code == 200

        # Customer 2 tries to get 1 more — should fail
        c2 = await _create_customer(async_client)
        r2 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": c2},
        )
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_concurrent_prepare_only_one_succeeds_when_one_item_left(
        self, async_client: AsyncClient
    ):
        _, _, group_id = await _create_owner(async_client)
        # Consume 9 of 10
        c0 = await _create_customer(async_client)
        await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 9},
            cookies={"moaorder_token": c0},
        )

        c1 = await _create_customer(async_client)
        c2 = await _create_customer(async_client)

        results = await asyncio.gather(
            async_client.post(
                "/api/checkout/prepare",
                json={"group_id": group_id, "quantity": 1},
                cookies={"moaorder_token": c1},
            ),
            async_client.post(
                "/api/checkout/prepare",
                json={"group_id": group_id, "quantity": 1},
                cookies={"moaorder_token": c2},
            ),
            return_exceptions=True,
        )

        statuses = [r.status_code for r in results if hasattr(r, "status_code")]
        assert statuses.count(200) == 1
        assert statuses.count(409) == 1

    @pytest.mark.asyncio
    async def test_prepare_requires_auth(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
        )
        assert resp.status_code == 401


class TestWebhook:
    @pytest.mark.asyncio
    async def test_webhook_creates_order(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        # Prepare
        prepare_resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 2},
            cookies={"moaorder_token": customer_token},
        )
        assert prepare_resp.status_code == 200
        payment_id = prepare_resp.json()["payment_id"]
        amount = prepare_resp.json()["amount"]

        # Mock PortOne API response
        mock_payment_info = {
            "paymentId": payment_id,
            "status": "PAID",
            "amount": {"total": amount},
        }

        payload = json.dumps(
            {"type": "Transaction.Paid", "data": {"paymentId": payment_id}}
        ).encode()
        signature = _make_webhook_signature(payload)

        with patch(
            "app.api.webhooks.get_payment",
            new_callable=AsyncMock,
            return_value=mock_payment_info,
        ):
            webhook_resp = await async_client.post(
                "/api/webhooks/portone",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-portone-signature": signature,
                },
            )

        assert webhook_resp.status_code == 200

        # Verify order via by-payment endpoint
        order_resp = await async_client.get(
            f"/api/orders/by-payment/{payment_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.status_code == 200
        assert order_resp.json()["status"] == "paid"
        assert order_resp.json()["order_id"]

    @pytest.mark.asyncio
    async def test_webhook_idempotent_duplicate_call(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        prepare_resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
        payment_id = prepare_resp.json()["payment_id"]
        amount = prepare_resp.json()["amount"]

        mock_payment_info = {
            "paymentId": payment_id,
            "status": "PAID",
            "amount": {"total": amount},
        }
        payload = json.dumps(
            {"type": "Transaction.Paid", "data": {"paymentId": payment_id}}
        ).encode()
        signature = _make_webhook_signature(payload)

        with patch(
            "app.api.webhooks.get_payment",
            new_callable=AsyncMock,
            return_value=mock_payment_info,
        ):
            r1 = await async_client.post(
                "/api/webhooks/portone",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-portone-signature": signature,
                },
            )
            r2 = await async_client.post(
                "/api/webhooks/portone",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-portone-signature": signature,
                },
            )

        assert r1.status_code == 200
        assert r2.status_code == 200

        # Only one order created
        order_resp = await async_client.get(
            f"/api/orders/by-payment/{payment_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.status_code == 200
        assert order_resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_rejected(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        prepare_resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
        payment_id = prepare_resp.json()["payment_id"]

        payload = json.dumps(
            {"type": "Transaction.Paid", "data": {"paymentId": payment_id}}
        ).encode()

        resp = await async_client.post(
            "/api/webhooks/portone",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-portone-signature": "v1=invalidsignature",
            },
        )
        assert resp.status_code == 401


class TestOrderByPayment:
    @pytest.mark.asyncio
    async def test_processing_status_before_webhook(self, async_client: AsyncClient):
        _, _, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        prepare_resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
        payment_id = prepare_resp.json()["payment_id"]

        resp = await async_client.get(
            f"/api/orders/by-payment/{payment_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"
        assert resp.json()["order_id"] is None

    @pytest.mark.asyncio
    async def test_not_found_for_unknown_payment(self, async_client: AsyncClient):
        customer_token = await _create_customer(async_client)
        resp = await async_client.get(
            "/api/orders/by-payment/nonexistent-id",
            cookies={"moaorder_token": customer_token},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_auto_subscription_created_after_payment(
        self, async_client: AsyncClient
    ):
        _, store_id, group_id = await _create_owner(async_client)
        customer_token = await _create_customer(async_client)

        prepare_resp = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": customer_token},
        )
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
            await async_client.post(
                "/api/webhooks/portone",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-portone-signature": signature,
                },
            )

        # Customer should now be subscribed to the store
        subs_resp = await async_client.get(
            "/api/subscriptions/my",
            cookies={"moaorder_token": customer_token},
        )
        assert subs_resp.status_code == 200
        body = subs_resp.json()
        subs_list = body if isinstance(body, list) else body.get("items", [])
        store_ids = [s["store_id"] for s in subs_list]
        assert store_id in store_ids
