from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# --- Helpers ---


def _make_kakao_info(suffix: str = "") -> dict:
    return {
        "kakao_id": f"test_{uuid.uuid4().hex[:8]}{suffix}",
        "nickname": "테스트사장님",
        "profile_image": None,
    }


async def _create_owner(client: AsyncClient) -> tuple[str, str]:
    """Create a user, onboard as owner, return (token, store_id)."""
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


def _future_dt(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_dt(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Group Creation ---


class TestGroupCreate:
    @pytest.mark.asyncio
    async def test_create_group_returns_public_id(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)

        resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "수제 쿠키",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "public_id" in data
        assert len(data["public_id"]) == 12
        assert data["product_name"] == "수제 쿠키"
        assert data["price"] == 5000
        assert data["status"] == "open"
        assert data["type"] == "reservation"

    @pytest.mark.asyncio
    async def test_create_group_with_max_quantity(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "한정판 빵",
                "price": 8000,
                "closes_at": _future_dt(),
                "max_quantity": 50,
            },
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["max_quantity"] == 50
        assert data["remaining_qty"] == 50

    @pytest.mark.asyncio
    async def test_create_pickup_group_with_slots(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "픽업 케이크",
                "price": 30000,
                "closes_at": _future_dt(),
                "type": "pickup",
                "pickup_slots": [
                    {
                        "label": "오전 10-12시",
                        "start_at": _future_dt(48),
                        "end_at": _future_dt(50),
                    },
                    {
                        "label": "오후 2-4시",
                        "start_at": _future_dt(52),
                        "end_at": _future_dt(54),
                    },
                ],
            },
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "pickup"
        assert len(data["pickup_slots"]) == 2

    @pytest.mark.asyncio
    async def test_customer_cannot_create_group(self, async_client: AsyncClient):
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

        resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "테스트",
                "price": 1000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 403


# --- Public Group View ---


class TestPublicGroup:
    @pytest.mark.asyncio
    async def test_get_public_group_by_public_id(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "공개 조회 테스트",
                "price": 10000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        public_id = create_resp.json()["public_id"]

        resp = await async_client.get(f"/api/public/groups/{public_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_id"] == public_id
        assert data["product_name"] == "공개 조회 테스트"
        assert data["store_name"] == "테스트매장"

    @pytest.mark.asyncio
    async def test_get_nonexistent_public_group_returns_404(self, async_client: AsyncClient):
        resp = await async_client.get("/api/public/groups/nonexistent1")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_store_public_groups(self, async_client: AsyncClient):
        token, store_id = await _create_owner(async_client)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "공구1",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "공구2",
                "price": 8000,
                "closes_at": _future_dt(48),
            },
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(f"/api/public/stores/{store_id}/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


# --- Group Update Restrictions ---


class TestGroupUpdate:
    @pytest.mark.asyncio
    async def test_update_product_name_and_price(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "원래 이름",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        resp = await async_client.patch(
            f"/api/groups/{group_id}",
            json={"product_name": "새 이름", "price": 6000},
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["product_name"] == "새 이름"
        assert data["price"] == 6000

    @pytest.mark.asyncio
    async def test_cannot_update_closed_group(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "마감 테스트",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        # Close group
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        # Try to update
        resp = await async_client.patch(
            f"/api/groups/{group_id}",
            json={"product_name": "변경 시도"},
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 400


# --- Group Delete ---


class TestGroupDelete:
    @pytest.mark.asyncio
    async def test_delete_open_group_no_orders(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "삭제 테스트",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]
        public_id = create_resp.json()["public_id"]

        resp = await async_client.delete(
            f"/api/groups/{group_id}",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 204

        # Verify deleted via public API
        resp = await async_client.get(f"/api/public/groups/{public_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_closed_group(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "마감 삭제 테스트",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.delete(
            f"/api/groups/{group_id}",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 400


# --- Group Status Transitions ---


class TestGroupStatusTransitions:
    @pytest.mark.asyncio
    async def test_close_group(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "조기 마감",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    @pytest.mark.asyncio
    async def test_pickup_ready_after_close(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "수령 가능 테스트",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.post(
            f"/api/groups/{group_id}/pickup-ready",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pickup_ready"

    @pytest.mark.asyncio
    async def test_complete_group(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "완료 테스트",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.post(
            f"/api/groups/{group_id}/complete",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cannot_close_already_closed(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "중복 마감",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 400


# --- My Groups ---


class TestMyGroups:
    @pytest.mark.asyncio
    async def test_list_my_groups(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "내 공구 1",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        await async_client.post(
            "/api/groups",
            json={
                "product_name": "내 공구 2",
                "price": 8000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/groups/my",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_my_groups_filter_status(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        create_resp = await async_client.post(
            "/api/groups",
            json={
                "product_name": "필터 테스트 1",
                "price": 5000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )
        group_id = create_resp.json()["id"]

        await async_client.post(
            "/api/groups",
            json={
                "product_name": "필터 테스트 2",
                "price": 8000,
                "closes_at": _future_dt(),
            },
            cookies={"moaorder_token": token},
        )

        # Close first group
        await async_client.post(
            f"/api/groups/{group_id}/close",
            cookies={"moaorder_token": token},
        )

        resp = await async_client.get(
            "/api/groups/my?status=open",
            cookies={"moaorder_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "open"


# --- Presign Upload ---


class TestPresignUpload:
    @pytest.mark.asyncio
    async def test_presign_returns_urls(self, async_client: AsyncClient):
        token, _ = await _create_owner(async_client)

        with patch(
            "app.api.uploads.generate_presigned_upload",
            return_value=(
                "https://r2.example.com/presigned-upload-url",
                "https://cdn.example.com/groups/test.jpg",
            ),
        ):
            resp = await async_client.post(
                "/api/uploads/presign",
                json={
                    "filename": "photo.jpg",
                    "content_type": "image/jpeg",
                },
                cookies={"moaorder_token": token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "public_url" in data
