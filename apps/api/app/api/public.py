from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.group import GroupPublicResponse
from app.services.group import (
    _group_public_response,
    get_public_group,
    list_store_public_groups,
)

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/groups/{public_id}", response_model=GroupPublicResponse)
async def get_public_group_endpoint(
    public_id: str,
    db: AsyncSession = Depends(get_db),
) -> GroupPublicResponse:
    result = await get_public_group(public_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    group, store_name = result
    return _group_public_response(group, store_name)


@router.get("/stores/{store_id}/groups", response_model=list[GroupPublicResponse])
async def list_store_groups_endpoint(
    store_id: uuid.UUID,
    status: Optional[str] = Query(None),
    sort: str = Query("closes_at"),
    db: AsyncSession = Depends(get_db),
) -> list[GroupPublicResponse]:
    rows = await list_store_public_groups(store_id, status, sort, db)
    return [_group_public_response(group, store_name) for group, store_name in rows]
