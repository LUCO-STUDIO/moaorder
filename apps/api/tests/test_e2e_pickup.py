"""
E2E test: Pickup-type (픽업형) group buy flow.

시나리오:
공구 생성 (픽업형 + 시간대 2개)
→ 고객 주문 (시간대 선택) → 결제
→ 마감 → 수령 가능
→ 피킹 리스트 시간대별 확인
→ 완료
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


def _slot_dt(offset_hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


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
            "store_name": "픽업 테스트매장",
            "owner_name": "사장님",
            "contact": "010-5555-6666",
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


async def _place_order_with_slot(
    client: AsyncClient,
    group_id: str,
    customer_token: str,
    quantity: int,
    pickup_slot_id: str | None = None,
) -> str:
    """Prepare + fire webhook with optional slot. Returns order_id."""
    body: dict = {"group_id": group_id, "quantity": quantity}
    if pickup_slot_id:
        body["pickup_slot_id"] = pickup_slot_id

    prep = await client.post(
        "/api/checkout/prepare",
        json=body,
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


class TestPickupTypeE2E:
    @pytest.mark.asyncio
    async def test_pickup_type_with_two_slots(self, async_client: AsyncClient):
        """픽업형 공구 + 시간대 2개, 각 시간대에 고객 배정 후 피킹 리스트 시간대별 확인."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        # 시간대 2개 정의
        slot1_start = _slot_dt(24)
        slot1_end = _slot_dt(25)
        slot2_start = _slot_dt(26)
        slot2_end = _slot_dt(27)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "픽업 쿠키",
                "price": 5000,
                "type": "pickup",
                "closes_at": _future_dt(20),
                "max_quantity": 20,
                "pickup_slots": [
                    {
                        "label": "오전 픽업",
                        "start_at": slot1_start,
                        "end_at": slot1_end,
                        "sort_order": 0,
                    },
                    {
                        "label": "오후 픽업",
                        "start_at": slot2_start,
                        "end_at": slot2_end,
                        "sort_order": 1,
                    },
                ],
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201, group_resp.text
        group_data = group_resp.json()
        group_id = group_data["id"]

        # 시간대 ID 추출
        slots = group_data["pickup_slots"]
        assert len(slots) == 2
        slot1_id = slots[0]["id"]
        slot2_id = slots[1]["id"]

        # 고객 A: 오전 픽업
        c_morning = await _login_and_onboard_customer(async_client)
        order_morning = await _place_order_with_slot(
            async_client, group_id, c_morning, quantity=2, pickup_slot_id=slot1_id
        )

        # 고객 B: 오후 픽업
        c_afternoon = await _login_and_onboard_customer(async_client)
        order_afternoon = await _place_order_with_slot(
            async_client, group_id, c_afternoon, quantity=1, pickup_slot_id=slot2_id
        )

        # 마감
        close_resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

        # CONFIRMED 확인
        for oid, ct in [(order_morning, c_morning), (order_afternoon, c_afternoon)]:
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "confirmed"

        # 수령 가능
        pickup_ready_resp = await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        assert pickup_ready_resp.status_code == 200
        assert pickup_ready_resp.json()["status"] == "pickup_ready"

        # 피킹 리스트 확인 (총 수량)
        picking = await async_client.get(
            f"/api/groups/{group_id}/picking-list",
            cookies={"moaorder_token": owner_token},
        )
        assert picking.status_code == 200
        picking_data = picking.json()
        assert picking_data["total_quantity"] == 3  # 2 + 1
        assert len(picking_data["items"]) == 2  # 2명 주문

        # slot_groups 필드 존재 확인 (pickup 타입은 slot_groups 반환)
        assert "slot_groups" in picking_data

        # 완료
        complete_resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"

        # 수령 처리 안 한 주문들은 not_picked_up
        for oid, ct in [(order_morning, c_morning), (order_afternoon, c_afternoon)]:
            order_resp = await async_client.get(
                f"/api/orders/{oid}",
                cookies={"moaorder_token": ct},
            )
            assert order_resp.json()["status"] == "not_picked_up"

    @pytest.mark.asyncio
    async def test_pickup_type_mark_picked_up_by_slot(self, async_client: AsyncClient):
        """픽업형: 한 시간대 수령 처리 → picked_up, 나머지 → not_picked_up."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "슬롯 수령 테스트",
                "price": 3000,
                "type": "pickup",
                "closes_at": _future_dt(20),
                "max_quantity": 10,
                "pickup_slots": [
                    {
                        "label": "1부",
                        "start_at": _slot_dt(10),
                        "end_at": _slot_dt(11),
                        "sort_order": 0,
                    },
                    {
                        "label": "2부",
                        "start_at": _slot_dt(12),
                        "end_at": _slot_dt(13),
                        "sort_order": 1,
                    },
                ],
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]
        slots = group_resp.json()["pickup_slots"]
        slot1_id = slots[0]["id"]
        slot2_id = slots[1]["id"]

        c1 = await _login_and_onboard_customer(async_client)
        c2 = await _login_and_onboard_customer(async_client)

        order1 = await _place_order_with_slot(
            async_client, group_id, c1, quantity=1, pickup_slot_id=slot1_id
        )
        order2 = await _place_order_with_slot(
            async_client, group_id, c2, quantity=1, pickup_slot_id=slot2_id
        )

        # close → pickup_ready
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )

        # order1만 수령 처리
        await async_client.post(
            f"/api/orders/{order1}/mark-picked-up",
            cookies={"moaorder_token": owner_token},
        )

        # 완료
        await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )

        r1 = await async_client.get(
            f"/api/orders/{order1}", cookies={"moaorder_token": c1}
        )
        r2 = await async_client.get(
            f"/api/orders/{order2}", cookies={"moaorder_token": c2}
        )
        assert r1.json()["status"] == "picked_up"
        assert r2.json()["status"] == "not_picked_up"

    @pytest.mark.asyncio
    async def test_pickup_type_without_slot_selection(self, async_client: AsyncClient):
        """픽업형이지만 슬롯 미선택 주문도 허용됨."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "슬롯 미선택 테스트",
                "price": 2000,
                "type": "pickup",
                "closes_at": _future_dt(24),
                "max_quantity": 10,
                "pickup_slots": [
                    {
                        "label": "아무 시간",
                        "start_at": _slot_dt(8),
                        "end_at": _slot_dt(9),
                        "sort_order": 0,
                    },
                ],
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        customer_token = await _login_and_onboard_customer(async_client)
        # 슬롯 미선택으로 주문
        order_id = await _place_order_with_slot(
            async_client, group_id, customer_token, quantity=1, pickup_slot_id=None
        )

        order_resp = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_resp.status_code == 200
        assert order_resp.json()["status"] == "paid"
