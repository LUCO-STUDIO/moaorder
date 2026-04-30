"""
E2E test: Group-buy type (공동구매형) flow.

달성 시나리오:
공구 생성 (공동구매형, min_quantity=3) → 3명 주문
→ 마감 → 전원 CONFIRMED → 피킹 → 완료

미달 시나리오:
공구 생성 (공동구매형, min_quantity=3) → 2명 주문
→ 마감 → 전원 CANCELLED + 환불 + 알림
"""
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kakao_info() -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}",
        "nickname": "테스트유저",
        "profile_image": None,
    }


def _future_dt(hours: int = 48) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _make_signature(payload: bytes) -> str:
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


async def _login_and_onboard_owner(client: AsyncClient) -> tuple[str, str]:
    kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        resp = await client.post("/api/auth/kakao/exchange", json={"code": "code"})
    token = resp.cookies["moaorder_token"]

    onboard = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": "공동구매 테스트매장",
            "owner_name": "사장님",
            "contact": "010-3333-4444",
            "region": "서울",
            "category": "베이커리",
        },
        cookies={"moaorder_token": token},
    )
    assert onboard.status_code == 200
    token = onboard.cookies.get("moaorder_token", token)
    store_id = onboard.json()["store_id"]
    return token, store_id


async def _login_and_onboard_customer(client: AsyncClient) -> str:
    kakao_info = _make_kakao_info()
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        resp = await client.post("/api/auth/kakao/exchange", json={"code": "code"})
    token = resp.cookies["moaorder_token"]

    onboard = await client.post(
        "/api/onboarding/customer",
        json={"nickname": "고객", "region": "서울", "category": "베이커리"},
        cookies={"moaorder_token": token},
    )
    assert onboard.status_code == 200
    return onboard.cookies.get("moaorder_token", token)


async def _place_order(
    client: AsyncClient,
    group_id: str,
    customer_token: str,
    quantity: int,
) -> str:
    """Prepare + fire webhook. Returns order_id."""
    prep = await client.post(
        "/api/checkout/prepare",
        json={"group_id": group_id, "quantity": quantity},
        cookies={"moaorder_token": customer_token},
    )
    assert prep.status_code == 200, prep.text
    payment_id = prep.json()["payment_id"]
    amount = prep.json()["amount"]

    payload = json.dumps(
        {"type": "Transaction.Paid", "data": {"paymentId": payment_id}}
    ).encode()

    with patch(
        "app.api.webhooks.get_payment",
        new_callable=AsyncMock,
        return_value={"paymentId": payment_id, "status": "PAID", "amount": {"total": amount}},
    ):
        wh = await client.post(
            "/api/webhooks/portone",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-portone-signature": _make_signature(payload),
            },
        )
    assert wh.status_code == 200, wh.text

    by_payment = await client.get(
        f"/api/orders/by-payment/{payment_id}",
        cookies={"moaorder_token": customer_token},
    )
    assert by_payment.status_code == 200
    order_id = by_payment.json()["order_id"]
    assert order_id is not None
    return order_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGroupBuyAchieved:
    @pytest.mark.asyncio
    async def test_min_qty_met_all_confirmed_and_complete(self, async_client: AsyncClient):
        """달성 시나리오: min_quantity=3, 3명 주문 → 마감 → 전원 CONFIRMED → 피킹 → 완료."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "공동구매 쿠키",
                "price": 4000,
                "type": "group_buy",
                "closes_at": _future_dt(48),
                "max_quantity": 20,
                "min_quantity": 3,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201, group_resp.text
        group_id = group_resp.json()["id"]

        # 3명 주문 (각각 1개씩 → 합계 3개 ≥ min_quantity)
        customers = [await _login_and_onboard_customer(async_client) for _ in range(3)]
        order_ids = []
        for ct in customers:
            oid = await _place_order(async_client, group_id, ct, quantity=1)
            order_ids.append(oid)

        # 마감 → 달성됨 → 전원 CONFIRMED
        close_resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

        for oid, ct in zip(order_ids, customers):
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "confirmed", (
                f"order {oid} status: {order_resp.json()['status']}"
            )

        # 피킹 리스트 확인
        picking = await async_client.get(
            f"/api/groups/{group_id}/picking-list",
            cookies={"moaorder_token": owner_token},
        )
        assert picking.status_code == 200
        assert picking.json()["total_quantity"] == 3

        # 수령 가능 → 모두 수령 처리
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        for oid in order_ids:
            await async_client.post(
                f"/api/orders/{oid}/mark-picked-up",
                cookies={"moaorder_token": owner_token},
            )

        # 완료
        complete_resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"

        # 전원 PICKED_UP
        for oid, ct in zip(order_ids, customers):
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "picked_up"


class TestGroupBuyNotAchieved:
    @pytest.mark.asyncio
    async def test_min_qty_not_met_all_cancelled_and_refunded(self, async_client: AsyncClient):
        """미달 시나리오: min_quantity=3, 2명 주문 → 마감 → 전원 CANCELLED + 환불."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "미달 공동구매",
                "price": 6000,
                "type": "group_buy",
                "closes_at": _future_dt(48),
                "max_quantity": 20,
                "min_quantity": 3,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201, group_resp.text
        group_id = group_resp.json()["id"]

        # 2명만 주문 → 합계 2 < min_quantity=3
        customers = [await _login_and_onboard_customer(async_client) for _ in range(2)]
        order_ids = []
        for ct in customers:
            oid = await _place_order(async_client, group_id, ct, quantity=1)
            order_ids.append(oid)

        # 마감 → 미달 → 공구 CANCELLED + 전원 CANCELLED + 환불
        with patch(
            "app.services.refund.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-min-qty-not-met",
        ):
            close_resp = await async_client.post(
                f"/api/groups/{group_id}/close",
                cookies={"moaorder_token": owner_token},
            )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "cancelled"

        # 전원 CANCELLED
        for oid, ct in zip(order_ids, customers):
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "cancelled", (
                f"order {oid} expected cancelled but got {order_resp.json()['status']}"
            )

        # 취소 알림 확인
        for ct in customers:
            notifs = await async_client.get(
                "/api/notifications",
                cookies={"moaorder_token": ct},
            )
            assert notifs.status_code == 200
            notif_types = [n["type"] for n in notifs.json()["items"]]
            assert any(
                t in notif_types
                for t in ("order_cancelled_min_qty", "group_cancelled_min_qty")
            ), f"Expected cancellation notification, got: {notif_types}"

    @pytest.mark.asyncio
    async def test_min_qty_met_exactly_at_boundary(self, async_client: AsyncClient):
        """정확히 min_quantity 달성 → 성공."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "경계값 공구",
                "price": 5000,
                "type": "group_buy",
                "closes_at": _future_dt(24),
                "max_quantity": 10,
                "min_quantity": 2,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        # 정확히 2명 주문 (min_quantity=2)
        customers = [await _login_and_onboard_customer(async_client) for _ in range(2)]
        order_ids = [
            await _place_order(async_client, group_id, ct, quantity=1)
            for ct in customers
        ]

        close_resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

        for oid, ct in zip(order_ids, customers):
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "confirmed"
