from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, verify_store_ownership
from app.core.database import get_db
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreResponse, StoreUpdateRequest

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")
    return StoreResponse(
        id=str(store.id),
        name=store.name,
        region=store.region,
        category=store.category,
        contact=store.contact,
        owner_id=str(store.owner_id),
    )


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: uuid.UUID,
    body: StoreUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    await verify_store_ownership(store_id, current_user, db)

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")

    if body.name is not None:
        store.name = body.name
    if body.region is not None:
        store.region = body.region
    if body.category is not None:
        store.category = body.category
    if body.contact is not None:
        store.contact = body.contact
    await db.commit()
    await db.refresh(store)

    return StoreResponse(
        id=str(store.id),
        name=store.name,
        region=store.region,
        category=store.category,
        contact=store.contact,
        owner_id=str(store.owner_id),
    )
