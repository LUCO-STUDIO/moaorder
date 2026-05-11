"""Kakao Local API reverse-geocode for GPS 동네 인증.

Kakao Local docs:
  https://developers.kakao.com/docs/latest/ko/local/dev-guide#coord-to-region

We use the coord2regioncode endpoint which returns 시도(1)/시군구(2)/읍면동(3)
hierarchy for a given lng/lat. The response contains both administrative ("H")
and legal ("B") region codes; we pick the first administrative one because
moaorder regions are user-facing names.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

KAKAO_LOCAL_BASE = "https://dapi.kakao.com"


class RegionResolution(BaseModel):
    region_1depth: str  # 예: 서울특별시
    region_2depth: str  # 예: 강남구
    region_3depth: str  # 예: 역삼동


class GeoConfigError(RuntimeError):
    """Raised when KAKAO_REST_API_KEY is not configured."""


class GeoLookupError(RuntimeError):
    """Raised when Kakao Local API call fails or returns no result."""


async def reverse_geocode(lng: float, lat: float) -> RegionResolution:
    """Resolve coordinates to a Korean region triple via Kakao Local API.

    Raises GeoConfigError if no API key configured, GeoLookupError on any
    API/network failure or empty result.
    """
    if not settings.KAKAO_REST_API_KEY:
        raise GeoConfigError("KAKAO_REST_API_KEY가 설정되지 않았습니다")

    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    params = {"x": str(lng), "y": str(lat)}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{KAKAO_LOCAL_BASE}/v2/local/geo/coord2regioncode.json",
                headers=headers,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise GeoLookupError(f"카카오 Local API 호출 실패: {exc}") from exc

    if resp.status_code != 200:
        raise GeoLookupError(
            f"카카오 Local API 오류: status={resp.status_code} body={resp.text[:200]}"
        )

    body = resp.json()
    docs = body.get("documents") or []
    # Prefer administrative region (region_type == "H"), fall back to whatever
    # the API returns first.
    chosen: Optional[dict] = next(
        (d for d in docs if d.get("region_type") == "H"), None
    )
    if chosen is None and docs:
        chosen = docs[0]

    if not chosen:
        raise GeoLookupError("좌표에서 행정구역을 찾지 못했습니다")

    return RegionResolution(
        region_1depth=chosen.get("region_1depth_name") or "",
        region_2depth=chosen.get("region_2depth_name") or "",
        region_3depth=chosen.get("region_3depth_name") or "",
    )


def region_matches(stored_region: Optional[str], resolved: RegionResolution) -> bool:
    """Decide whether the stored region matches the resolved coordinates.

    Comparison anchors on 시군구 (region_2depth) because 시도 alone is too broad
    (e.g. "서울특별시 마포구" ≠ "서울특별시 강남구" yet share 1depth). 3depth alone
    is too narrow because users typically don't type 동 in their profile.
    """
    if not stored_region or not resolved.region_2depth:
        return False
    s = stored_region.replace(" ", "")
    return resolved.region_2depth.replace(" ", "") in s
