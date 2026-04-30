from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_owner, verify_store_ownership
from app.core.database import get_db
from app.models.store import StoreMember
from app.models.user import User
from app.schemas.common import GroupStatus, PaginatedResponse
from app.schemas.group import (
    GroupCreateRequest,
    GroupResponse,
    GroupUpdateRequest,
)
from app.services.group import (
    _group_response,
    close_group,
    complete_group,
    create_group,
    delete_group,
    get_group_with_ownership,
    list_my_groups,
    set_pickup_ready,
    update_group,
)
from app.services.notification import notify_store_subscribers

router = APIRouter(prefix="/groups", tags=["groups"])


async def _get_owner_store_id(
    current_user: User,
    db: AsyncSession,
) -> uuid.UUID:
    from sqlalchemy import select

    result = await db.execute(
        select(StoreMember.store_id).where(
            StoreMember.user_id == current_user.id,
            StoreMember.role == "owner",
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="매장을 찾을 수 없습니다")
    return row[0]


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group_endpoint(
    body: GroupCreateRequest,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    store_id = await _get_owner_store_id(current_user, db)
    group = await create_group(store_id, body, db)

    await notify_store_subscribers(
        db,
        store_id=store_id,
        group_id=group.id,
        notification_type="group_opened",
        title=f"새 공구가 열렸어요",
        body=f"{group.product_name} - {group.price:,}원",
        payload={"group_id": str(group.id)},
    )
    await db.commit()

    return _group_response(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group_endpoint(
    group_id: uuid.UUID,
    body: GroupUpdateRequest,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    store_id = await _get_owner_store_id(current_user, db)
    group = await get_group_with_ownership(group_id, store_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    try:
        updated, price_changed, closes_at_changed = await update_group(group, body, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if price_changed or closes_at_changed:
        changes = []
        if price_changed:
            changes.append("가격")
        if closes_at_changed:
            changes.append("마감시간")
        change_text = ", ".join(changes)

        from sqlalchemy import select

        from app.models.order import Order

        result = await db.execute(
            select(Order.user_id)
            .where(Order.group_id == group_id, Order.status != "cancelled")
            .distinct()
        )
        orderer_ids = [row[0] for row in result.all()]

        from app.services.notification import create_notification

        for user_id in orderer_ids:
            await create_notification(
                db,
                user_id=user_id,
                notification_type="group_updated",
                title=f"공구 변경: {updated.product_name}",
                body=f"{change_text}이(가) 변경되었습니다",
                store_id=store_id,
                group_id=group_id,
                payload={"group_id": str(group_id)},
                dedupe_key=f"group_updated:{group_id}:{user_id}:{change_text}",
            )
        await db.commit()

    return _group_response(updated)


@router.delete("/{group_id}", status_code=204)
async def delete_group_endpoint(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> None:
    store_id = await _get_owner_store_id(current_user, db)
    group = await get_group_with_ownership(group_id, store_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    try:
        await delete_group(group, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{group_id}/close", response_model=GroupResponse)
async def close_group_endpoint(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    store_id = await _get_owner_store_id(current_user, db)
    group = await get_group_with_ownership(group_id, store_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    try:
        updated = await close_group(group, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _group_response(updated)


@router.post("/{group_id}/pickup-ready", response_model=GroupResponse)
async def pickup_ready_endpoint(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    store_id = await _get_owner_store_id(current_user, db)
    group = await get_group_with_ownership(group_id, store_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    try:
        updated = await set_pickup_ready(group, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _group_response(updated)


@router.post("/{group_id}/complete", response_model=GroupResponse)
async def complete_group_endpoint(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_owner)],
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    store_id = await _get_owner_store_id(current_user, db)
    group = await get_group_with_ownership(group_id, store_id, db)
    if not group:
        raise HTTPException(status_code=404, detail="공구를 찾을 수 없습니다")

    try:
        updated = await complete_group(group, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _group_response(updated)


@router.get("/my", response_model=PaginatedResponse[GroupResponse])
async def list_my_groups_endpoint(
    current_user: Annotated[User, Depends(require_owner)],
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[GroupResponse]:
    store_id = await _get_owner_store_id(current_user, db)
    groups, total = await list_my_groups(store_id, status, page, limit, db)

    return PaginatedResponse(
        items=[_group_response(g) for g in groups],
        total=total,
        page=page,
        limit=limit,
    )
