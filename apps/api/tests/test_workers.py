from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.idempotency import IdempotencyKey
from app.models.inventory import InventoryHold
from app.models.notification import Notification
from app.models.order import Order
from app.models.store import Store
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kakao_id() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def _future(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


async def _create_base(db: AsyncSession) -> dict:
    """Create owner, store, open group, and a paid order."""
    owner = User(kakao_id=_make_kakao_id(), role="owner", nickname="사장님")
    db.add(owner)
    await db.flush()

    customer = User(kakao_id=_make_kakao_id(), role="customer", nickname="고객님")
    db.add(customer)
    await db.flush()

    store = Store(owner_id=owner.id, name=f"테스트매장_{uuid.uuid4().hex[:4]}")
    db.add(store)
    await db.flush()

    group = Group(
        public_id=uuid.uuid4().hex[:12],
        store_id=store.id,
        product_name="테스트상품",
        price=10000,
        closes_at=_past(10),  # already expired
    )
    db.add(group)
    await db.flush()

    order = Order(
        group_id=group.id,
        user_id=customer.id,
        store_id=store.id,
        status="paid",
        quantity=2,
        total_amount=20000,
        current_quantity=2,
        current_amount=20000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    return {
        "owner": owner,
        "customer": customer,
        "store": store,
        "group": group,
        "order": order,
    }


# ---------------------------------------------------------------------------
# Auto-close: normal close → CONFIRMED
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_close_normal(db: AsyncSession) -> None:
    """open group with closes_at in the past → group CLOSED, order CONFIRMED."""
    records = await _create_base(db)
    group = records["group"]
    order = records["order"]
    await db.commit()

    from app.workers.auto_close import _run

    await _run(db)

    await db.refresh(group)
    await db.refresh(order)

    assert group.status == "closed"
    assert order.status == "confirmed"


# ---------------------------------------------------------------------------
# Auto-close: group_buy min_qty not met → CANCELLED + refund
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_close_min_qty_not_met(db: AsyncSession) -> None:
    """group_buy with min_qty not met → group CANCELLED, orders CANCELLED."""
    owner = User(kakao_id=_make_kakao_id(), role="owner", nickname="사장님2")
    db.add(owner)
    await db.flush()

    customer = User(kakao_id=_make_kakao_id(), role="customer", nickname="고객2")
    db.add(customer)
    await db.flush()

    store = Store(owner_id=owner.id, name=f"테스트매장_{uuid.uuid4().hex[:4]}")
    db.add(store)
    await db.flush()

    group = Group(
        public_id=uuid.uuid4().hex[:12],
        store_id=store.id,
        product_name="공구상품",
        price=5000,
        closes_at=_past(10),
        type="group_buy",
        min_quantity=10,
    )
    db.add(group)
    await db.flush()

    order = Order(
        group_id=group.id,
        user_id=customer.id,
        store_id=store.id,
        status="paid",
        quantity=1,
        total_amount=5000,
        current_quantity=1,
        current_amount=5000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()
    await db.commit()

    from app.workers.auto_close import _run

    with patch("app.services.refund.process_full_refund", return_value="refund_id"):
        await _run(db)

    await db.refresh(group)
    await db.refresh(order)

    assert group.status == "cancelled"
    assert order.status == "cancelled"


# ---------------------------------------------------------------------------
# Notification send: pending inapp → sent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_send_inapp(db: AsyncSession) -> None:
    """pending inapp notification → status=sent, sent_at set."""
    notif = Notification(
        user_id=None,
        type="order_confirmed",
        channel="inapp",
        title="주문 확정",
        scheduled_at=_past(5),
    )
    db.add(notif)
    await db.flush()
    await db.commit()

    from app.workers.notification_sender import _run

    await _run(db)

    await db.refresh(notif)
    assert notif.status == "sent"
    assert notif.sent_at is not None


# ---------------------------------------------------------------------------
# Notification send: future scheduled_at → still pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_send_skips_future(db: AsyncSession) -> None:
    """Notification with scheduled_at in the future should not be sent yet."""
    notif = Notification(
        user_id=None,
        type="pickup_reminder_customer",
        channel="inapp",
        title="픽업 리마인더",
        scheduled_at=_future(3600),
    )
    db.add(notif)
    await db.flush()
    await db.commit()

    from app.workers.notification_sender import _run

    await _run(db)

    await db.refresh(notif)
    assert notif.status == "pending"


# ---------------------------------------------------------------------------
# Email send: Resend mock → sent + provider_message_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_send_email(db: AsyncSession) -> None:
    """pending email notification → Resend called → status=sent, provider_message_id set."""
    notif = Notification(
        user_id=None,
        type="order_confirmed",
        channel="email",
        title="주문이 확정됐어요",
        body="<p>확정</p>",
        payload={"email": "test@example.com"},
        scheduled_at=_past(5),
    )
    db.add(notif)
    await db.flush()
    await db.commit()

    fake_msg_id = f"resend_{uuid.uuid4().hex}"

    with patch("app.services.email.resend.Emails.send", return_value={"id": fake_msg_id}):
        from app.workers.notification_sender import _run
        await _run(db)

    await db.refresh(notif)
    assert notif.status == "sent"
    assert notif.provider_message_id == fake_msg_id
    assert notif.sent_at is not None


# ---------------------------------------------------------------------------
# Hold expiry: active + expired → expired + remaining_qty restored
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hold_expiry(db: AsyncSession) -> None:
    """Active hold with expires_at in the past → status=expired, remaining_qty restored."""
    owner = User(kakao_id=_make_kakao_id(), role="owner", nickname="사장님3")
    db.add(owner)
    await db.flush()

    store = Store(owner_id=owner.id, name=f"매장_{uuid.uuid4().hex[:4]}")
    db.add(store)
    await db.flush()

    customer = User(kakao_id=_make_kakao_id(), role="customer", nickname="고객3")
    db.add(customer)
    await db.flush()

    group = Group(
        public_id=uuid.uuid4().hex[:12],
        store_id=store.id,
        product_name="홀드상품",
        price=1000,
        closes_at=_future(3600),
        max_quantity=20,
        remaining_qty=5,
    )
    db.add(group)
    await db.flush()

    hold = InventoryHold(
        group_id=group.id,
        user_id=customer.id,
        quantity=3,
        expires_at=_past(10),
        status="active",
    )
    db.add(hold)
    await db.flush()
    await db.commit()

    from app.workers.hold_cleaner import _run

    await _run(db)

    await db.refresh(hold)
    await db.refresh(group)

    assert hold.status == "expired"
    assert group.remaining_qty == 8  # 5 + 3


# ---------------------------------------------------------------------------
# Idempotency cleanup: expired keys deleted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idempotency_cleanup(db: AsyncSession) -> None:
    """Expired idempotency keys are deleted; non-expired ones survive."""
    expired_key = IdempotencyKey(
        key=f"expired_{uuid.uuid4().hex}",
        resource_type="order",
        status_code=200,
        expires_at=_past(10),
    )
    active_key = IdempotencyKey(
        key=f"active_{uuid.uuid4().hex}",
        resource_type="order",
        status_code=200,
        expires_at=_future(3600),
    )
    db.add(expired_key)
    db.add(active_key)
    await db.flush()
    await db.commit()

    from app.workers.idempotency_cleaner import _run

    await _run(db)

    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == expired_key.key)
    )
    assert result.scalar_one_or_none() is None

    result2 = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == active_key.key)
    )
    assert result2.scalar_one_or_none() is not None
