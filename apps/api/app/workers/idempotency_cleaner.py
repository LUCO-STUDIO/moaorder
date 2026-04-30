from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.idempotency import IdempotencyKey

logger = logging.getLogger(__name__)


async def process_expired_idempotency() -> None:
    """Delete expired idempotency keys."""
    async with async_session_factory() as db:
        await _run(db)


async def _run(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(IdempotencyKey)
        .where(IdempotencyKey.expires_at <= now)
        .returning(IdempotencyKey.key)
    )
    deleted_count = len(result.fetchall())

    if deleted_count:
        await db.commit()

    logger.info("[idempotency_cleaner] Deleted %d expired keys", deleted_count)
