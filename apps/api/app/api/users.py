from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserUpdateRequest
from app.services.geo import (
    GeoConfigError,
    GeoLookupError,
    region_matches,
    reverse_geocode,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    region_changed = body.region is not None and body.region != current_user.region

    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.region is not None:
        current_user.region = body.region
    if body.category is not None:
        current_user.category = body.category

    # Changing region invalidates the prior GPS verification — they're verifying
    # a different place now.
    if region_changed:
        current_user.region_verified_at = None

    await db.commit()

    return {
        "id": str(current_user.id),
        "nickname": current_user.nickname,
        "region": current_user.region,
        "category": current_user.category,
    }


class VerifyRegionRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class VerifyRegionResponse(BaseModel):
    matched: bool
    detected_region: str  # full "{1depth} {2depth} {3depth}" for UI display
    detected_2depth: str  # 시군구 only — main comparison unit
    verified_at: Optional[datetime]


@router.post("/me/verify-region", response_model=VerifyRegionResponse)
async def verify_region(
    body: VerifyRegionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> VerifyRegionResponse:
    """Resolve client's GPS to a Korean administrative region and, if it
    matches the user's registered region, stamp ``region_verified_at``.

    Mismatches are NOT auto-applied — the client decides whether to update
    the user's region to the detected one. This avoids surprises if someone
    is briefly traveling outside their home district.
    """
    try:
        resolved = await reverse_geocode(lng=body.lng, lat=body.lat)
    except GeoConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeoLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    matched = region_matches(current_user.region, resolved)
    verified_at = current_user.region_verified_at

    if matched:
        now = datetime.now(timezone.utc)
        current_user.region_verified_at = now
        await db.commit()
        verified_at = now

    detected_full = " ".join(
        part
        for part in (resolved.region_1depth, resolved.region_2depth, resolved.region_3depth)
        if part
    )

    return VerifyRegionResponse(
        matched=matched,
        detected_region=detected_full,
        detected_2depth=resolved.region_2depth,
        verified_at=verified_at,
    )
