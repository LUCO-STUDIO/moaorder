"""Fire-and-forget operational alerting via Discord webhook.

Used for events that need a human's attention but should never fail the
underlying request: signature mismatches (potential attack), payment data
inconsistencies, refund API errors. The alert call always swallows errors so
the caller's flow is never affected by alerting infrastructure.

Set ``DISCORD_OPS_WEBHOOK_URL`` to enable; left empty in dev so tests and
local runs don't spam the channel.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_LEVEL_PREFIX: dict[AlertLevel, str] = {
    AlertLevel.INFO: "ℹ️",
    AlertLevel.WARNING: "⚠️",
    AlertLevel.CRITICAL: "🚨",
}


async def notify(
    message: str,
    *,
    level: AlertLevel = AlertLevel.WARNING,
    context: Optional[dict] = None,
) -> None:
    """Post an ops alert to Discord. No-op if no webhook configured.

    The whole call is best-effort: any HTTP/network/encoding failure is
    logged and swallowed.
    """
    url = settings.DISCORD_OPS_WEBHOOK_URL
    if not url:
        return

    prefix = _LEVEL_PREFIX.get(level, "")
    body = f"{prefix} **{level.value.upper()}** — {message}"
    if context:
        ctx_lines = "\n".join(f"  • `{k}`: `{v}`" for k, v in context.items())
        body = f"{body}\n{ctx_lines}"

    # Discord caps content at 2000 chars.
    body = body[:1990]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json={"content": body})
    except Exception as exc:
        logger.warning("[ops_alert] Discord notify failed: %s", exc)


def notify_sync(
    message: str,
    *,
    level: AlertLevel = AlertLevel.WARNING,
    context: Optional[dict] = None,
) -> None:
    """Schedule an alert from sync code (e.g. workers without an event loop)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None or not loop.is_running():
        # No loop available — block on a fresh one. Acceptable here because
        # this path is only used outside the request lifecycle.
        asyncio.run(notify(message, level=level, context=context))
        return

    loop.create_task(notify(message, level=level, context=context))
