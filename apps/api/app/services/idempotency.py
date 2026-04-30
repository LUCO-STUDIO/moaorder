import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey


async def get_idempotency_key(
    key: str,
    db: AsyncSession,
) -> Optional[IdempotencyKey]:
    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key)
    )
    return result.scalar_one_or_none()


async def save_idempotency_key(
    key: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID],
    status_code: int,
    ttl_days: int,
    db: AsyncSession,
) -> IdempotencyKey:
    record = IdempotencyKey(
        key=key,
        resource_type=resource_type,
        resource_id=resource_id,
        status_code=status_code,
        expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
    )
    db.add(record)
    await db.flush()
    return record
