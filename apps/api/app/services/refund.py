from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.order import Order

PORTONE_API_BASE = "https://api.portone.io"


async def process_partial_refund(order: Order, refund_amount: int) -> str | None:
    """Call PortOne V2 partial cancel API.

    Returns the cancellation ID (or payment_id as fallback).
    Raises ValueError on PortOne API error.
    """
    if not order.payment_id:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PORTONE_API_BASE}/payments/{order.payment_id}/cancel",
            headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"},
            json={"reason": "고객 요청 부분 취소", "amount": refund_amount},
            timeout=15.0,
        )

    if resp.status_code != 200:
        raise ValueError(f"PortOne 부분환불 실패: {resp.status_code} {resp.text}")

    data = resp.json()
    cancellations = data.get("cancellations") or []
    if cancellations:
        last = cancellations[-1]
        return last.get("pgCancellationId") or last.get("id") or order.payment_id
    return order.payment_id


async def process_full_refund(order: Order) -> str | None:
    """Call PortOne V2 full cancel API.

    Returns the cancellation ID (or payment_id as fallback).
    Raises ValueError on PortOne API error.
    """
    if not order.payment_id:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PORTONE_API_BASE}/payments/{order.payment_id}/cancel",
            headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"},
            json={"reason": "고객 요청 전체 취소"},
            timeout=15.0,
        )

    if resp.status_code != 200:
        raise ValueError(f"PortOne 전액환불 실패: {resp.status_code} {resp.text}")

    data = resp.json()
    cancellations = data.get("cancellations") or []
    if cancellations:
        last = cancellations[-1]
        return last.get("pgCancellationId") or last.get("id") or order.payment_id
    return order.payment_id
