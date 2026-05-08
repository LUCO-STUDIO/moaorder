from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.group import Group
from app.models.notification import Notification
from app.models.order import Order
from app.models.store import Store
from app.models.user import User


def _future_dt(hours: int = 48) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _make_kakao_id() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


async def _create_test_records(db: AsyncSession) -> dict:
    """Create user, store, group, order records for FK-safe notification tests."""
    user = User(kakao_id=_make_kakao_id(), role="customer", nickname="테스트")
    db.add(user)
    await db.flush()

    owner = User(kakao_id=_make_kakao_id(), role="owner", nickname="사장님")
    db.add(owner)
    await db.flush()

    store = Store(owner_id=owner.id, name="테스트매장")
    db.add(store)
    await db.flush()

    group = Group(
        public_id=uuid.uuid4().hex[:12],
        store_id=store.id,
        product_name="테스트상품",
        price=10000,
        closes_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(group)
    await db.flush()

    order = Order(
        group_id=group.id,
        user_id=user.id,
        store_id=store.id,
        status="paid",
        quantity=1,
        total_amount=10000,
        current_quantity=1,
        current_amount=10000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    return {
        "user": user,
        "owner": owner,
        "store": store,
        "group": group,
        "order": order,
    }


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _login(client: AsyncClient, kakao_id: str | None = None) -> str:
    from tests.conftest import kakao_login

    return await kakao_login(client, kakao_id=kakao_id)


async def _setup_owner(client: AsyncClient) -> tuple[str, str, str]:
    """Returns (token, store_id, group_id)."""
    token = await _login(client)
    ob = await client.post(
        "/api/onboarding/owner",
        json={
            "store_name": f"테스트매장_{uuid.uuid4().hex[:4]}",
            "owner_name": "사장님",
            "contact": "010-0000-0000",
            "region": "서울",
            "category": "베이커리",
        },
        cookies={"moaorder_token": token},
    )
    assert ob.status_code == 200
    token = ob.cookies.get("moaorder_token", token)
    store_id = ob.json()["store_id"]

    grp = await client.post(
        "/api/groups",
        json={
            "product_name": "공구상품",
            "price": 10000,
            "closes_at": _future_dt(48),
            "type": "reservation",
        },
        cookies={"moaorder_token": token},
    )
    assert grp.status_code == 201
    group_id = grp.json()["id"]
    return token, store_id, group_id


async def _setup_customer(client: AsyncClient) -> tuple[str, str]:
    """Returns (token, user_id)."""
    token = await _login(client)
    ob = await client.post(
        "/api/onboarding/customer",
        json={"nickname": "고객님", "region": "서울", "category": "베이커리"},
        cookies={"moaorder_token": token},
    )
    assert ob.status_code == 200
    token = ob.cookies.get("moaorder_token", token)
    user_id = ob.json()["user_id"]
    return token, user_id


# ---------------------------------------------------------------------------
# Tests: notification service (dedupe, cancel helpers)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_notification_dedupe(db):
    """Same dedupe_key creates one notification; second call returns None."""
    from app.services.notification import create_notification

    dedupe_key = f"test_dedupe:{uuid.uuid4()}"

    # user_id is optional on Notification, pass None to avoid FK constraint
    first = await create_notification(
        db,
        user_id=None,
        notification_type="test",
        title="알림 1",
        dedupe_key=dedupe_key,
    )
    await db.flush()
    assert first is not None

    second = await create_notification(
        db,
        user_id=None,
        notification_type="test",
        title="알림 2",
        dedupe_key=dedupe_key,
    )
    assert second is None  # duplicate blocked


@pytest.mark.asyncio
async def test_create_notification_no_dedupe(db):
    """Without dedupe_key, multiple notifications are created."""
    from app.services.notification import create_notification

    n1 = await create_notification(db, user_id=None, notification_type="test", title="A")
    n2 = await create_notification(db, user_id=None, notification_type="test", title="B")
    await db.flush()
    assert n1 is not None
    assert n2 is not None


@pytest.mark.asyncio
async def test_cancel_pending_notifications_for_order(db):
    """cancel_pending_notifications_for_order only cancels the matching order's pending notifs."""
    from app.services.notification import (
        cancel_pending_notifications_for_order,
        create_notification,
    )

    records = await _create_test_records(db)
    order = records["order"]

    # Create a second user + order for comparison (same group_id + different user avoids unique index)
    user2 = User(kakao_id=_make_kakao_id(), role="customer", nickname="고객2")
    db.add(user2)
    await db.flush()

    order2 = Order(
        group_id=records["group"].id,
        user_id=user2.id,
        store_id=records["store"].id,
        status="paid",
        quantity=1,
        total_amount=10000,
        current_quantity=1,
        current_amount=10000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order2)
    await db.flush()

    n1 = await create_notification(
        db, user_id=None, notification_type="t", title="for order", order_id=order.id
    )
    n2 = await create_notification(
        db, user_id=None, notification_type="t", title="other", order_id=order2.id
    )
    await db.flush()
    assert n1 is not None
    assert n2 is not None

    cancelled = await cancel_pending_notifications_for_order(db, order.id)
    assert cancelled == 1

    await db.refresh(n1)
    await db.refresh(n2)
    assert n1.status == "cancelled"
    assert n2.status == "pending"


@pytest.mark.asyncio
async def test_cancel_pending_notifications_for_group(db):
    """cancel_pending_notifications_for_group cancels matching pending notifs."""
    from app.services.notification import (
        cancel_pending_notifications_for_group,
        create_notification,
    )

    records = await _create_test_records(db)
    group = records["group"]

    n1 = await create_notification(
        db, user_id=None, notification_type="t", title="for group", group_id=group.id
    )
    await db.flush()
    assert n1 is not None

    cancelled = await cancel_pending_notifications_for_group(db, group.id)
    assert cancelled == 1

    await db.refresh(n1)
    assert n1.status == "cancelled"


# ---------------------------------------------------------------------------
# Tests: notification API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notifications_list_empty(async_client):
    """New user has empty notification list."""
    token, _ = await _setup_customer(async_client)

    resp = await async_client.get(
        "/api/notifications",
        cookies={"moaorder_token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["unread_count"] == 0


@pytest.mark.asyncio
async def test_unread_count_endpoint(async_client):
    """GET /api/notifications/unread-count returns numeric count."""
    token, _ = await _setup_customer(async_client)

    resp = await async_client.get(
        "/api/notifications/unread-count",
        cookies={"moaorder_token": token},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["unread_count"], int)


@pytest.mark.asyncio
async def test_mark_read_not_found(async_client):
    """Marking a non-existent notification returns 404."""
    token, _ = await _setup_customer(async_client)

    fake_id = uuid.uuid4()
    resp = await async_client.post(
        f"/api/notifications/{fake_id}/read",
        cookies={"moaorder_token": token},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_read_all_returns_zero(async_client):
    """POST /api/notifications/read-all returns unread_count=0."""
    token, _ = await _setup_customer(async_client)

    resp = await async_client.post(
        "/api/notifications/read-all",
        cookies={"moaorder_token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_group_open_notifies_subscribers(async_client, db):
    """Creating a group sends group_opened notifications to subscribed customers."""
    owner_token, store_id, _ = await _setup_owner(async_client)

    customer_token, _ = await _setup_customer(async_client)
    sub_resp = await async_client.post(
        "/api/subscriptions",
        json={"store_id": store_id},
        cookies={"moaorder_token": customer_token},
    )
    assert sub_resp.status_code in (200, 201)

    grp_resp = await async_client.post(
        "/api/groups",
        json={
            "product_name": "새 공구 상품",
            "price": 5000,
            "closes_at": _future_dt(24),
            "type": "reservation",
        },
        cookies={"moaorder_token": owner_token},
    )
    assert grp_resp.status_code == 201
    new_group_id = grp_resp.json()["id"]

    result = await db.execute(
        select(Notification).where(
            Notification.group_id == uuid.UUID(new_group_id),
            Notification.type == "group_opened",
        )
    )
    notifs = result.scalars().all()
    assert len(notifs) >= 1


@pytest.mark.asyncio
async def test_group_close_notifies_orderer_and_owner(async_client, db):
    """Closing a group sends order_confirmed to orderer and picking_list_ready to owner."""
    owner_token, store_id, group_id = await _setup_owner(async_client)
    _, customer_user_id = await _setup_customer(async_client)

    from app.models.order import Order

    order = Order(
        group_id=uuid.UUID(group_id),
        user_id=uuid.UUID(customer_user_id),
        store_id=uuid.UUID(store_id),
        status="paid",
        quantity=1,
        total_amount=10000,
        current_quantity=1,
        current_amount=10000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    close_resp = await async_client.post(
        f"/api/groups/{group_id}/close",
        cookies={"moaorder_token": owner_token},
    )
    assert close_resp.status_code == 200

    confirmed = await db.execute(
        select(Notification).where(
            Notification.order_id == order.id,
            Notification.type == "order_confirmed",
        )
    )
    assert confirmed.scalar_one_or_none() is not None

    picking = await db.execute(
        select(Notification).where(
            Notification.group_id == uuid.UUID(group_id),
            Notification.type == "picking_list_ready",
        )
    )
    assert picking.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_order_cancel_cancels_pending_notifs(async_client, db):
    """Cancelling a pre-close order cancels its pending notifications."""
    owner_token, store_id, group_id = await _setup_owner(async_client)
    customer_token, customer_user_id = await _setup_customer(async_client)

    from app.models.order import Order

    order = Order(
        group_id=uuid.UUID(group_id),
        user_id=uuid.UUID(customer_user_id),
        store_id=uuid.UUID(store_id),
        status="paid",
        quantity=1,
        total_amount=10000,
        current_quantity=1,
        current_amount=10000,
        payment_id=f"pay_{uuid.uuid4().hex}",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    pending_notif = Notification(
        user_id=uuid.UUID(customer_user_id),
        order_id=order.id,
        type="pickup_reminder_customer",
        title="픽업 리마인더",
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(pending_notif)
    await db.commit()
    await db.refresh(pending_notif)
    assert pending_notif.status == "pending"

    with patch("app.api.orders.process_full_refund", new_callable=AsyncMock, return_value="refund_id"):
        cancel_resp = await async_client.post(
            f"/api/orders/{order.id}/cancel",
            cookies={"moaorder_token": customer_token},
        )
    assert cancel_resp.status_code == 200

    await db.refresh(pending_notif)
    assert pending_notif.status == "cancelled"


@pytest.mark.asyncio
async def test_notification_read_and_read_all(async_client, db):
    """Mark single notification read, then mark-all-read brings count to 0."""
    _, user_id = await _setup_customer(async_client)

    # Get the customer token separately
    token = await _login(async_client)
    ob = await async_client.post(
        "/api/onboarding/customer",
        json={"nickname": "읽음테스트2", "region": "서울", "category": "베이커리"},
        cookies={"moaorder_token": token},
    )
    token = ob.cookies.get("moaorder_token", token)
    user_id2 = ob.json()["user_id"]

    # Insert 2 sent notifications for this user
    n1 = Notification(
        user_id=uuid.UUID(user_id2),
        type="test",
        title="알림1",
        status="sent",
        scheduled_at=datetime.now(timezone.utc),
    )
    n2 = Notification(
        user_id=uuid.UUID(user_id2),
        type="test",
        title="알림2",
        status="sent",
        scheduled_at=datetime.now(timezone.utc),
    )
    db.add(n1)
    db.add(n2)
    await db.commit()
    await db.refresh(n1)
    await db.refresh(n2)

    count_resp = await async_client.get(
        "/api/notifications/unread-count", cookies={"moaorder_token": token}
    )
    assert count_resp.json()["unread_count"] == 2

    # Mark one read
    read_resp = await async_client.post(
        f"/api/notifications/{n1.id}/read", cookies={"moaorder_token": token}
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["read_at"] is not None

    count_resp2 = await async_client.get(
        "/api/notifications/unread-count", cookies={"moaorder_token": token}
    )
    assert count_resp2.json()["unread_count"] == 1

    # Mark all read
    all_resp = await async_client.post(
        "/api/notifications/read-all", cookies={"moaorder_token": token}
    )
    assert all_resp.status_code == 200
    assert all_resp.json()["unread_count"] == 0

    count_resp3 = await async_client.get(
        "/api/notifications/unread-count", cookies={"moaorder_token": token}
    )
    assert count_resp3.json()["unread_count"] == 0
