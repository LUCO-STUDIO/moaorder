from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.group import Group
from app.models.inventory import InventoryHold

logger = logging.getLogger(__name__)


async def process_expired_holds() -> None:
    """Expire active holds whose expires_at <= now() and restore remaining_qty."""
    async with async_session_factory() as db:
        await _run(db)


async def _run(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(InventoryHold).where(
            InventoryHold.status == "active",
            InventoryHold.expires_at <= now,
        )
    )
    holds = list(result.scalars().all())

    expired_count = 0
    for hold in holds:
        try:
            hold.status = "expired"

            # Restore remaining_qty on the group
            grp_result = await db.execute(
                select(Group).where(Group.id == hold.group_id)
            )
            group = grp_result.scalar_one_or_none()
            if group is not None and group.remaining_qty is not None:
                group.remaining_qty = group.remaining_qty + hold.quantity

            expired_count += 1
        except Exception as exc:
            logger.error("[error] process_expired_holds hold %s: %s", hold.id, exc)

    if expired_count:
        await db.commit()

    logger.info("[hold_cleaner] Expired %d holds, restored qty", expired_count)
