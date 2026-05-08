from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.checkout import confirm_payment
from app.services.ops_alert import AlertLevel, notify
from app.services.payment import get_payment, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/portone", status_code=200)
async def portone_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_portone_signature: str = Header(default=""),
) -> dict:
    payload = await request.body()

    # 1. Signature verification — header MUST be present in every request.
    #    Skipping when missing would let an attacker forge webhooks for any
    #    paymentId they happen to know.
    if not x_portone_signature or not verify_webhook_signature(payload, x_portone_signature):
        await notify(
            "PortOne 웹훅 서명 검증 실패",
            level=AlertLevel.CRITICAL,
            context={
                "missing_header": not bool(x_portone_signature),
                "client": request.client.host if request.client else "?",
            },
        )
        raise HTTPException(status_code=401, detail="웹훅 서명 검증 실패")

    # 2. Parse payload
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 요청 형식입니다")

    # Support PortOne V2 webhook format: {type, data: {paymentId, ...}}
    webhook_type = data.get("type", "")
    inner = data.get("data", data)  # fallback to root if no "data" key
    payment_id = inner.get("paymentId") or inner.get("payment_id")

    if not payment_id:
        logger.warning("portone webhook: paymentId 없음, type=%s", webhook_type)
        return {"ok": True}

    # Only process paid events
    if webhook_type and webhook_type not in ("Transaction.Paid", ""):
        logger.info("portone webhook: 처리 대상 아님, type=%s", webhook_type)
        return {"ok": True}

    # 3. Verify payment via PortOne API
    try:
        payment_info = await get_payment(payment_id)
    except ValueError as e:
        logger.error("portone 결제 조회 실패: %s", e)
        raise HTTPException(status_code=502, detail="결제 정보 조회 실패") from e

    portone_status = payment_info.get("status", "")
    amount_obj = payment_info.get("amount", {})
    portone_amount = amount_obj.get("total", 0) if isinstance(amount_obj, dict) else int(amount_obj)

    if portone_status != "PAID":
        logger.info("portone webhook: 결제 상태 PAID 아님, status=%s", portone_status)
        return {"ok": True}

    # 4. Confirm payment — idempotent via UNIQUE constraint on orders.payment_id.
    #    confirm_payment ValueErrors (missing hold, amount mismatch, status mismatch)
    #    are all non-retryable, so we ack with 200 and log; replying 4xx/5xx would
    #    only cause PortOne to retry the same broken payload forever.
    try:
        await confirm_payment(
            payment_id=payment_id,
            portone_status=portone_status,
            portone_amount=portone_amount,
            db=db,
        )
    except ValueError as e:
        logger.error("주문 생성 실패 (재시도 불가): payment_id=%s error=%s", payment_id, e)
        await notify(
            "주문 확정 실패 — 결제 데이터 불일치 (수동 정산 필요)",
            level=AlertLevel.CRITICAL,
            context={"payment_id": payment_id, "reason": str(e)},
        )

    return {"ok": True}
