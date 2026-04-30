from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db
from app.models.store import Store, StoreMember
from app.models.user import User
from app.schemas.onboarding import CustomerOnboardingRequest, OwnerOnboardingRequest

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

COOKIE_MAX_AGE = 7 * 24 * 60 * 60


@router.post("/owner")
async def onboard_owner(
    body: OwnerOnboardingRequest,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    if current_user.role == "owner" and current_user.stores:
        raise HTTPException(status_code=400, detail="이미 매장이 등록되어 있습니다")

    current_user.role = "owner"
    current_user.nickname = body.owner_name
    current_user.phone = body.contact
    current_user.region = body.region
    current_user.category = body.category

    store = Store(
        owner_id=current_user.id,
        name=body.store_name,
        region=body.region,
        category=body.category,
        contact=body.contact,
    )
    db.add(store)
    await db.flush()

    member = StoreMember(
        store_id=store.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)
    await db.commit()
    await db.refresh(store)

    token = create_access_token(current_user.id, current_user.role)
    response.set_cookie(
        key="moaorder_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    return {
        "user_id": str(current_user.id),
        "store_id": str(store.id),
        "role": current_user.role,
    }


@router.post("/customer")
async def onboard_customer(
    body: CustomerOnboardingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    current_user.nickname = body.nickname
    if body.region is not None:
        current_user.region = body.region
    if body.category is not None:
        current_user.category = body.category
    await db.commit()

    return {
        "user_id": str(current_user.id),
        "role": current_user.role,
    }
