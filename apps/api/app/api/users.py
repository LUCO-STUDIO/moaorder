from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.region is not None:
        current_user.region = body.region
    if body.category is not None:
        current_user.category = body.category
    await db.commit()

    return {
        "id": str(current_user.id),
        "nickname": current_user.nickname,
        "region": current_user.region,
        "category": current_user.category,
    }
