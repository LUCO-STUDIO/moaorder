from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.inventory import InventoryHold
from app.models.order import Order
from app.models.user import User
from app.schemas.checkout import (
    CheckoutPrepareRequest,
    CheckoutPrepareResponse,
    PaymentStatusResponse,
)
from app.services.checkout import (
    GroupNotAvailableError,
    SoldOutError,
    confirm_payment,
    prepare_checkout,
)
from app.services.payment import get_payment

logger = logging.getLogger(__name__)

router = APIRouter(tags=["checkout"])


@router.post("/checkout/prepare", response_model=CheckoutPrepareResponse, status_code=200)
async def checkout_prepare(
    body: CheckoutPrepareRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> CheckoutPrepareResponse:
    try:
        return await prepare_checkout(
            user_id=current_user.id,
            group_id=body.group_id,
            quantity=body.quantity,
            pickup_slot_id=body.pickup_slot_id,
            db=db,
        )
    except GroupNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SoldOutError as e:
        raise HTTPException(
            status_code=409,
            detail={"code": "SOLD_OUT", "message": str(e)},
        ) from e


@router.get("/orders/by-payment/{payment_id}", response_model=PaymentStatusResponse)
async def order_by_payment(
    payment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> PaymentStatusResponse:
    # 1) Order exists → paid
    order_result = await db.execute(
        select(Order).where(
            Order.payment_id == payment_id,
            Order.user_id == current_user.id,
        )
    )
    order = order_result.scalar_one_or_none()
    if order is not None:
        return PaymentStatusResponse(status="paid", order_id=str(order.id))

    # 2) Hold exists but no order yet — query PortOne directly as webhook fallback.
    #    This lets local dev work without tunneling (ngrok etc.) since PortOne
    #    cannot reach localhost. In prod the webhook usually wins this race.
    hold_result = await db.execute(
        select(InventoryHold).where(
            InventoryHold.portone_payment_id == payment_id,
            InventoryHold.user_id == current_user.id,
        )
    )
    hold = hold_result.scalar_one_or_none()
    if hold is None:
        raise HTTPException(status_code=404, detail="결제 정보를 찾을 수 없습니다")

    try:
        payment_info = await get_payment(payment_id)
    except Exception as e:
        logger.warning("by-payment: PortOne 조회 실패 payment_id=%s err=%s", payment_id, e)
        return PaymentStatusResponse(status="processing")

    portone_status = payment_info.get("status", "")
    amount_obj = payment_info.get("amount", {})
    portone_amount = (
        amount_obj.get("total", 0) if isinstance(amount_obj, dict) else int(amount_obj or 0)
    )

    if portone_status == "PAID":
        try:
            created = await confirm_payment(
                payment_id=payment_id,
                portone_status=portone_status,
                portone_amount=portone_amount,
                db=db,
            )
            return PaymentStatusResponse(status="paid", order_id=str(created.id))
        except ValueError as e:
            logger.error("by-payment: 주문 생성 실패 payment_id=%s err=%s", payment_id, e)

    return PaymentStatusResponse(status="processing")
