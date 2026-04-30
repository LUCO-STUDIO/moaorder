from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.group import Group

logger = logging.getLogger(__name__)


async def process_auto_close() -> None:
    """Close groups whose closes_at <= now()."""
    async with async_session_factory() as db:
        await _run(db)


async def _run(db: AsyncSession) -> None:
    from app.services.group import close_group

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Group).where(Group.status == "open", Group.closes_at <= now)
    )
    groups = list(result.scalars().all())

    for group in groups:
        try:
            closed = await close_group(group, db)
            confirmed_count = sum(
                1
                for _ in []  # close_group already handles orders internally
            )
            logger.info(
                "[auto_close] Closed group %s (status=%s)", group.id, closed.status
            )
        except Exception as exc:
            logger.error("[error] process_auto_close group %s: %s", group.id, exc)
