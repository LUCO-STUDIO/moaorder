"""
E2E test: Reservation-type group buy full flow.

시나리오:
사장님 로그인 → 매장 생성 → 공구 생성 (예약주문형)
→ 고객 로그인 → 공개 조회 (public_id) → checkout/prepare → 웹훅 mock → 주문 생성
→ 주문 상세 확인 → 수량 줄이기 → 부분환불 확인
→ 마감 (수동) → 주문 CONFIRMED
→ 사장님 피킹 리스트 확인 → 수령 가능 변경 → 고객 알림 확인
→ 수령 체크 → 공구 전체 완료 → PICKED_UP / NOT_PICKED_UP
→ 알림 이력 확인
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
    """Login + onboard owner. Returns (token, store_id)."""
    from tests.conftest import kakao_login

    token = await kakao_login(client)

    onboard = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": "예약주문 테스트매장",
            "owner_name": "사장님",
            "contact": "010-1111-2222",
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
    """Login + onboard customer. Returns token."""
    from tests.conftest import kakao_login

    token = await kakao_login(client)

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
) -> tuple[str, str]:
    """Prepare + fire webhook. Returns (order_id, payment_id)."""
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
    return order_id, payment_id


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestReservationTypeE2E:
    @pytest.mark.asyncio
    async def test_full_reservation_flow(self, async_client: AsyncClient):
        # 1. 사장님 로그인 + 매장 생성
        owner_token, store_id = await _login_and_onboard_owner(async_client)

        # 2. 공구 생성 (예약주문형, max_quantity=5)
        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "예약 쿠키",
                "price": 3000,
                "type": "reservation",
                "closes_at": _future_dt(48),
                "max_quantity": 5,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201, group_resp.text
        group_id = group_resp.json()["id"]
        public_id = group_resp.json()["public_id"]

        # 3. 고객 로그인 + 공개 조회 (public_id)
        customer_token = await _login_and_onboard_customer(async_client)

        public_resp = await async_client.get(f"/api/public/groups/{public_id}")
        assert public_resp.status_code == 200
        pub_data = public_resp.json()
        assert pub_data["product_name"] == "예약 쿠키"
        assert pub_data["group_id"] == group_id

        # 4. checkout/prepare → 웹훅 → 주문 생성
        order_id, payment_id = await _place_order(
            async_client, group_id, customer_token, quantity=3
        )

        # 5. 주문 상세 확인
        detail = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert data["status"] == "paid"
        assert data["current_quantity"] == 3
        assert data["current_amount"] == 9000  # 3 * 3000

        # 6. 수량 줄이기 (3 → 1) + 부분환불 확인
        with patch(
            "app.api.orders.process_partial_refund",
            new_callable=AsyncMock,
            return_value="refund-partial-001",
        ):
            reduce_resp = await async_client.post(
                f"/api/orders/{order_id}/reduce",
                json={"quantity_after": 1},
                cookies={"moaorder_token": customer_token},
            )
        assert reduce_resp.status_code == 200
        assert reduce_resp.json()["current_quantity"] == 1

        # 확인: 주문 상세에 반영
        detail2 = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert detail2.json()["current_quantity"] == 1
        assert detail2.json()["current_amount"] == 3000  # 1 * 3000

        # 7. 마감 (수동) → 주문 CONFIRMED
        close_resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

        order_after_close = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_after_close.json()["status"] == "confirmed"

        # 8. 사장님 피킹 리스트 확인
        picking = await async_client.get(
            f"/api/groups/{group_id}/picking-list",
            cookies={"moaorder_token": owner_token},
        )
        assert picking.status_code == 200
        picking_data = picking.json()
        assert picking_data["group_id"] == group_id
        assert picking_data["total_quantity"] == 1
        assert len(picking_data["items"]) == 1

        # 9. 수령 가능 변경
        pickup_ready_resp = await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        assert pickup_ready_resp.status_code == 200
        assert pickup_ready_resp.json()["status"] == "pickup_ready"

        order_pickup_ready = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert order_pickup_ready.json()["status"] == "pickup_ready"

        # 10. 고객 알림 확인 (pickup_ready 알림 존재)
        notifs = await async_client.get(
            "/api/notifications",
            cookies={"moaorder_token": customer_token},
        )
        assert notifs.status_code == 200
        notif_types = [n["type"] for n in notifs.json()["items"]]
        assert "pickup_ready" in notif_types

        # 11. 수령 체크 (사장님이 picked_up 처리)
        mark_resp = await async_client.post(
            f"/api/orders/{order_id}/mark-picked-up",
            cookies={"moaorder_token": owner_token},
        )
        assert mark_resp.status_code == 200

        # 12. 공구 전체 완료
        complete_resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"

        # 13. PICKED_UP 확인
        final_order = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert final_order.json()["status"] == "picked_up"

        # 14. 알림 이력 확인 (pickup_confirmed 포함)
        notifs2 = await async_client.get(
            "/api/notifications",
            cookies={"moaorder_token": customer_token},
        )
        assert notifs2.status_code == 200
        notif_types2 = [n["type"] for n in notifs2.json()["items"]]
        assert "pickup_confirmed" in notif_types2

    @pytest.mark.asyncio
    async def test_not_picked_up_when_unchecked_at_complete(self, async_client: AsyncClient):
        """고객이 수령하지 않은 경우 → NOT_PICKED_UP."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "미수령 테스트",
                "price": 2000,
                "type": "reservation",
                "closes_at": _future_dt(24),
                "max_quantity": 10,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        customer_token = await _login_and_onboard_customer(async_client)
        order_id, _ = await _place_order(async_client, group_id, customer_token, quantity=1)

        # close → pickup_ready → complete (mark-picked-up 없음)
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": owner_token},
        )
        await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": owner_token},
        )

        final = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert final.json()["status"] == "not_picked_up"

    @pytest.mark.asyncio
    async def test_cancel_then_reorder_same_group(self, async_client: AsyncClient):
        """취소 후 동일 공구 재주문 가능 확인."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "재주문 테스트 쿠키",
                "price": 5000,
                "type": "reservation",
                "closes_at": _future_dt(48),
                "max_quantity": 10,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        customer_token = await _login_and_onboard_customer(async_client)

        # 첫 주문
        order_id, _ = await _place_order(async_client, group_id, customer_token, quantity=2)

        # 취소
        with patch(
            "app.api.orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-cancel-001",
        ):
            cancel_resp = await async_client.post(
                f"/api/orders/{order_id}/cancel",
                cookies={"moaorder_token": customer_token},
            )
        assert cancel_resp.status_code == 200

        # 재주문 (잔여 수량 복원 확인)
        order_id2, _ = await _place_order(async_client, group_id, customer_token, quantity=1)

        detail = await async_client.get(
            f"/api/orders/{order_id2}",
            cookies={"moaorder_token": customer_token},
        )
        assert detail.status_code == 200
        assert detail.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_sold_out_cancel_restores_qty(self, async_client: AsyncClient):
        """max_quantity=1: 2번째 주문 실패 → 취소 → 3번째 성공."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "단 1개",
                "price": 10000,
                "type": "reservation",
                "closes_at": _future_dt(48),
                "max_quantity": 1,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        c1 = await _login_and_onboard_customer(async_client)
        c2 = await _login_and_onboard_customer(async_client)
        c3 = await _login_and_onboard_customer(async_client)

        # c1이 유일한 1개 선점
        order_id1, _ = await _place_order(async_client, group_id, c1, quantity=1)

        # c2는 품절로 실패
        prep2 = await async_client.post(
            "/api/checkout/prepare",
            json={"group_id": group_id, "quantity": 1},
            cookies={"moaorder_token": c2},
        )
        assert prep2.status_code == 409

        # c1 취소 → 잔여 복원
        with patch(
            "app.api.orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-restore-001",
        ):
            await async_client.post(
                f"/api/orders/{order_id1}/cancel",
                cookies={"moaorder_token": c1},
            )

        # c3 성공
        order_id3, _ = await _place_order(async_client, group_id, c3, quantity=1)
        detail3 = await async_client.get(
            f"/api/orders/{order_id3}",
            cookies={"moaorder_token": c3},
        )
        assert detail3.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_post_close_cancel_request_owner_approve_refund(
        self, async_client: AsyncClient
    ):
        """마감 후 취소 요청 → 사장님 승인 → 환불."""
        owner_token, _ = await _login_and_onboard_owner(async_client)

        group_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "사후 취소 테스트",
                "price": 4000,
                "type": "reservation",
                "closes_at": _future_dt(24),
                "max_quantity": 10,
            },
            cookies={"moaorder_token": owner_token},
        )
        assert group_resp.status_code == 201
        group_id = group_resp.json()["id"]

        customer_token = await _login_and_onboard_customer(async_client)
        order_id, _ = await _place_order(async_client, group_id, customer_token, quantity=2)

        # 마감 → CONFIRMED
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": owner_token},
        )

        # 고객 취소 요청
        req_resp = await async_client.post(
            f"/api/orders/{order_id}/cancel-request",
            json={"reason": "사정이 생겼어요"},
            cookies={"moaorder_token": customer_token},
        )
        assert req_resp.status_code == 200

        # 사장님 승인
        with patch(
            "app.api.owner_orders.process_full_refund",
            new_callable=AsyncMock,
            return_value="refund-approve-001",
        ):
            approve_resp = await async_client.post(
                f"/api/orders/{order_id}/approve-cancel",
                cookies={"moaorder_token": owner_token},
            )
        assert approve_resp.status_code == 200

        final = await async_client.get(
            f"/api/orders/{order_id}",
            cookies={"moaorder_token": customer_token},
        )
        assert final.json()["status"] == "cancelled"
