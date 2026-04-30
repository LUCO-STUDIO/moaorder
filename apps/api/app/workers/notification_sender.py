from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.notification import Notification

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


async def process_notifications() -> None:
    """Send pending notifications (inapp and email)."""
    async with async_session_factory() as db:
        await _run(db)


async def _run(db: AsyncSession) -> None:
    from app.services.email import send_email

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Notification)
        .where(
            Notification.status == "pending",
            Notification.scheduled_at <= now,
        )
        .limit(_BATCH_SIZE)
    )
    notifications = list(result.scalars().all())

    for notif in notifications:
        try:
            if notif.channel == "inapp":
                notif.status = "sent"
                notif.sent_at = now
                logger.info(
                    "[notification] Sent inapp to user %s: %s",
                    notif.user_id,
                    notif.type,
                )

            elif notif.channel == "email":
                to_addr = (notif.payload or {}).get("email") if notif.payload else None
                if not to_addr:
                    notif.status = "failed"
                    notif.failed_at = now
                    notif.error_message = "No email address in payload"
                    continue

                try:
                    msg_id = send_email(
                        to=to_addr,
                        subject=notif.title,
                        html_body=notif.body or notif.title,
                    )
                    notif.status = "sent"
                    notif.sent_at = now
                    notif.provider_message_id = msg_id
                    logger.info(
                        "[notification] Sent email to user %s: %s (msg_id=%s)",
                        notif.user_id,
                        notif.type,
                        msg_id,
                    )
                except Exception as email_exc:
                    notif.status = "failed"
                    notif.failed_at = now
                    notif.error_message = str(email_exc)
                    logger.error(
                        "[error] process_notifications email user %s: %s",
                        notif.user_id,
                        email_exc,
                    )

            else:
                # sms or unknown: mark sent (no-op for now)
                notif.status = "sent"
                notif.sent_at = now

        except Exception as exc:
            logger.error(
                "[error] process_notifications notif %s: %s", notif.id, exc
            )

    if notifications:
        await db.commit()
