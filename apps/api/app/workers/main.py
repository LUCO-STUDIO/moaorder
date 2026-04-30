import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run() -> None:
    from app.workers.auto_close import process_auto_close
    from app.workers.hold_cleaner import process_expired_holds
    from app.workers.idempotency_cleaner import process_expired_idempotency
    from app.workers.notification_sender import process_notifications

    logger.info("Worker started")
    while True:
        try:
            await process_auto_close()
        except Exception as exc:
            logger.error("[error] process_auto_close: %s", exc)

        try:
            await process_notifications()
        except Exception as exc:
            logger.error("[error] process_notifications: %s", exc)

        try:
            await process_expired_holds()
        except Exception as exc:
            logger.error("[error] process_expired_holds: %s", exc)

        try:
            await process_expired_idempotency()
        except Exception as exc:
            logger.error("[error] process_expired_idempotency: %s", exc)

        await asyncio.sleep(60)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
