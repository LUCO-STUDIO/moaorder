from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.geo import (
    GeoLookupError,
    RegionResolution,
    region_matches,
    reverse_geocode,
)


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- Pure helper: region_matches ---


class TestRegionMatches:
    def test_matches_when_2depth_present_in_stored(self) -> None:
        stored = "서울특별시 강남구"
        resolved = RegionResolution(
            region_1depth="서울특별시", region_2depth="강남구", region_3depth="역삼동"
        )
        assert region_matches(stored, resolved) is True

    def test_matches_when_only_2depth_typed(self) -> None:
        stored = "강남구"
        resolved = RegionResolution(
            region_1depth="서울특별시", region_2depth="강남구", region_3depth="역삼동"
        )
        assert region_matches(stored, resolved) is True

    def test_no_match_for_different_district(self) -> None:
        stored = "서울특별시 마포구"
        resolved = RegionResolution(
            region_1depth="서울특별시", region_2depth="강남구", region_3depth="역삼동"
        )
        assert region_matches(stored, resolved) is False

    def test_no_match_when_region_none(self) -> None:
        resolved = RegionResolution(
            region_1depth="서울특별시", region_2depth="강남구", region_3depth="역삼동"
        )
        assert region_matches(None, resolved) is False


# --- reverse_geocode (mocked httpx) ---


def _fake_kakao_response(documents: list[dict], status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value={"documents": documents})
    resp.text = ""
    return resp


@pytest.mark.asyncio
async def test_reverse_geocode_prefers_administrative_region() -> None:
    docs = [
        {
            "region_type": "B",
            "region_1depth_name": "서울특별시",
            "region_2depth_name": "강남구",
            "region_3depth_name": "역삼동",
        },
        {
            "region_type": "H",
            "region_1depth_name": "서울특별시",
            "region_2depth_name": "강남구",
            "region_3depth_name": "역삼1동",
        },
    ]
    fake_resp = _fake_kakao_response(docs)

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return fake_resp

    with patch("app.services.geo.settings") as mock_settings:
        mock_settings.KAKAO_REST_API_KEY = "test_key"
        with patch("app.services.geo.httpx.AsyncClient", FakeClient):
            result = await reverse_geocode(lng=127.0, lat=37.5)

    assert result.region_3depth == "역삼1동"  # H type wins


@pytest.mark.asyncio
async def test_reverse_geocode_raises_when_no_results() -> None:
    fake_resp = _fake_kakao_response([])

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return fake_resp

    with patch("app.services.geo.settings") as mock_settings:
        mock_settings.KAKAO_REST_API_KEY = "test_key"
        with patch("app.services.geo.httpx.AsyncClient", FakeClient):
            with pytest.raises(GeoLookupError):
                await reverse_geocode(lng=0, lat=0)


# --- Endpoint integration ---


import uuid


async def _signup_with_region(client: AsyncClient, region: str = "서울특별시 강남구") -> str:
    """Run the full email signup flow (send-code → verify → signup) and
    return the moaorder_token cookie so the caller can act as that user.
    """
    email = f"region_{uuid.uuid4().hex[:8]}@test.com"
    with (
        patch(
            "app.api.email_auth.generate_email_verification_code", return_value="123456"
        ),
        patch(
            "app.api.email_auth.send_verification_code_email", return_value="mock"
        ),
    ):
        send_resp = await client.post(
            "/api/auth/email/send-code", json={"email": email}
        )
        assert send_resp.status_code == 200, send_resp.text
        session_token = send_resp.json()["session_token"]

        verify_resp = await client.post(
            "/api/auth/email/verify-code",
            json={"session_token": session_token, "code": "123456"},
        )
        assert verify_resp.status_code == 200, verify_resp.text
        verified_email_token = verify_resp.json()["verified_email_token"]

        signup_resp = await client.post(
            "/api/auth/email/signup",
            json={
                "verified_email_token": verified_email_token,
                "password": "password123",
                "nickname": "테스트",
                "region": region,
            },
        )
    assert signup_resp.status_code == 200, signup_resp.text
    return signup_resp.cookies["moaorder_token"]


def _kakao_doc(d1: str, d2: str, d3: str) -> dict:
    return {
        "region_type": "H",
        "region_1depth_name": d1,
        "region_2depth_name": d2,
        "region_3depth_name": d3,
    }


@pytest.mark.asyncio
async def test_verify_region_succeeds_when_match(async_client: AsyncClient):
    token = await _signup_with_region(async_client, "서울특별시 강남구")

    mock_resolve = AsyncMock(
        return_value=RegionResolution(
            region_1depth="서울특별시",
            region_2depth="강남구",
            region_3depth="역삼동",
        )
    )
    with patch("app.api.users.reverse_geocode", mock_resolve):
        resp = await async_client.post(
            "/api/users/me/verify-region",
            json={"lat": 37.5, "lng": 127.0},
            cookies={"moaorder_token": token},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is True
    assert body["detected_2depth"] == "강남구"
    assert body["verified_at"] is not None

    # /auth/me should now report region_verified_at
    me = await async_client.get(
        "/api/auth/me", cookies={"moaorder_token": token}
    )
    assert me.json()["region_verified_at"] is not None


@pytest.mark.asyncio
async def test_verify_region_mismatch_does_not_mark_verified(
    async_client: AsyncClient,
):
    token = await _signup_with_region(async_client, "서울특별시 마포구")

    mock_resolve = AsyncMock(
        return_value=RegionResolution(
            region_1depth="서울특별시",
            region_2depth="강남구",
            region_3depth="역삼동",
        )
    )
    with patch("app.api.users.reverse_geocode", mock_resolve):
        resp = await async_client.post(
            "/api/users/me/verify-region",
            json={"lat": 37.5, "lng": 127.0},
            cookies={"moaorder_token": token},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is False
    assert body["verified_at"] is None
    assert body["detected_2depth"] == "강남구"


@pytest.mark.asyncio
async def test_verify_region_returns_503_when_no_api_key(async_client: AsyncClient):
    from app.services.geo import GeoConfigError

    token = await _signup_with_region(async_client, "서울특별시 강남구")

    mock_resolve = AsyncMock(side_effect=GeoConfigError("KAKAO_REST_API_KEY 미설정"))
    with patch("app.api.users.reverse_geocode", mock_resolve):
        resp = await async_client.post(
            "/api/users/me/verify-region",
            json={"lat": 37.5, "lng": 127.0},
            cookies={"moaorder_token": token},
        )

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_verify_region_validates_coordinates(async_client: AsyncClient):
    token = await _signup_with_region(async_client, "서울특별시 강남구")

    resp = await async_client.post(
        "/api/users/me/verify-region",
        json={"lat": 100, "lng": 200},  # out of WGS84 range
        cookies={"moaorder_token": token},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_region_change_invalidates_verification(async_client: AsyncClient):
    token = await _signup_with_region(async_client, "서울특별시 강남구")

    # First verify successfully.
    mock_resolve = AsyncMock(
        return_value=RegionResolution(
            region_1depth="서울특별시",
            region_2depth="강남구",
            region_3depth="역삼동",
        )
    )
    with patch("app.api.users.reverse_geocode", mock_resolve):
        await async_client.post(
            "/api/users/me/verify-region",
            json={"lat": 37.5, "lng": 127.0},
            cookies={"moaorder_token": token},
        )

    me_before = await async_client.get(
        "/api/auth/me", cookies={"moaorder_token": token}
    )
    assert me_before.json()["region_verified_at"] is not None

    # Now patch region — verification should be cleared.
    await async_client.patch(
        "/api/users/me",
        json={"region": "서울특별시 마포구"},
        cookies={"moaorder_token": token},
    )

    me_after = await async_client.get(
        "/api/auth/me", cookies={"moaorder_token": token}
    )
    assert me_after.json()["region_verified_at"] is None
