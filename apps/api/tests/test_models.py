import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models import (
    Base,
    Group,
    GroupPickupSlot,
    IdempotencyKey,
    InventoryHold,
    Notification,
    Order,
    OrderAdjustment,
    OrderEvent,
    Store,
    StoreMember,
    Subscription,
    User,
)

pytestmark = pytest.mark.asyncio


async def test_db_connection(engine):
    """DB 연결 테스트."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_all_tables_exist(engine):
    """12개 테이블 존재 확인."""
    expected_tables = {
        "users",
        "stores",
        "store_members",
        "subscriptions",
        "groups",
        "group_pickup_slots",
        "orders",
        "order_adjustments",
        "order_events",
        "notifications",
        "inventory_holds",
        "idempotency_keys",
    }
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        )
        actual_tables = {r[0] for r in result}

    assert expected_tables.issubset(actual_tables), (
        f"Missing tables: {expected_tables - actual_tables}"
    )


async def test_user_crud(db):
    """User 생성 기본 CRUD."""
    user = User(
        kakao_id="test_kakao_001",
        role="owner",
        nickname="테스트사장",
        phone="010-1234-5678",
    )
    db.add(user)
    await db.flush()

    assert user.id is not None
    assert user.created_at is not None
    assert user.role == "owner"


async def test_store_crud(db):
    """User → Store 생성."""
    user = User(kakao_id="test_kakao_002", role="owner", nickname="사장님")
    db.add(user)
    await db.flush()

    store = Store(owner_id=user.id, name="테스트매장", region="서울")
    db.add(store)
    await db.flush()

    assert store.id is not None
    assert store.owner_id == user.id


async def test_group_crud(db):
    """User → Store → Group 생성."""
    user = User(kakao_id="test_kakao_003", role="owner")
    db.add(user)
    await db.flush()

    store = Store(owner_id=user.id, name="테스트매장2")
    db.add(store)
    await db.flush()

    group = Group(
        public_id="abc123def456",
        store_id=store.id,
        status="open",
        type="reservation",
        product_name="맛있는 빵",
        price=15000,
        max_quantity=100,
        remaining_qty=100,
        closes_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    db.add(group)
    await db.flush()

    assert group.id is not None
    assert group.public_id == "abc123def456"
    assert group.remaining_qty == 100


async def test_order_active_unique_index(db):
    """같은 group_id+user_id로 active 주문 2개 생성 시 에러 확인."""
    user = User(kakao_id="test_kakao_004", role="customer")
    db.add(user)
    await db.flush()

    owner = User(kakao_id="test_kakao_005", role="owner")
    db.add(owner)
    await db.flush()

    store = Store(owner_id=owner.id, name="매장")
    db.add(store)
    await db.flush()

    group = Group(
        public_id="uniq_test_01",
        store_id=store.id,
        product_name="테스트상품",
        price=10000,
        closes_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(group)
    await db.flush()

    order1 = Order(
        group_id=group.id,
        user_id=user.id,
        store_id=store.id,
        status="paid",
        quantity=1,
        total_amount=10000,
        current_quantity=1,
        current_amount=10000,
    )
    db.add(order1)
    await db.flush()

    order2 = Order(
        group_id=group.id,
        user_id=user.id,
        store_id=store.id,
        status="confirmed",
        quantity=2,
        total_amount=20000,
        current_quantity=2,
        current_amount=20000,
    )
    db.add(order2)

    with pytest.raises(IntegrityError):
        await db.flush()


async def test_cancelled_order_allows_reorder(db):
    """취소된 주문 후 재주문 가능 확인."""
    user = User(kakao_id="test_kakao_006", role="customer")
    owner = User(kakao_id="test_kakao_007", role="owner")
    db.add_all([user, owner])
    await db.flush()

    store = Store(owner_id=owner.id, name="매장2")
    db.add(store)
    await db.flush()

    group = Group(
        public_id="reorder_tst1",
        store_id=store.id,
        product_name="재주문상품",
        price=5000,
        closes_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(group)
    await db.flush()

    # 첫 주문 (취소됨)
    order1 = Order(
        group_id=group.id,
        user_id=user.id,
        store_id=store.id,
        status="cancelled",
        quantity=1,
        total_amount=5000,
        current_quantity=0,
        current_amount=0,
    )
    db.add(order1)
    await db.flush()

    # 재주문 (활성) — partial unique index 덕분에 가능
    order2 = Order(
        group_id=group.id,
        user_id=user.id,
        store_id=store.id,
        status="paid",
        quantity=1,
        total_amount=5000,
        current_quantity=1,
        current_amount=5000,
    )
    db.add(order2)
    await db.flush()

    assert order2.id is not None


async def test_inventory_hold_active_unique(db):
    """같은 user+group에 active hold 2개 생성 시 에러."""
    user = User(kakao_id="test_kakao_008", role="customer")
    owner = User(kakao_id="test_kakao_009", role="owner")
    db.add_all([user, owner])
    await db.flush()

    store = Store(owner_id=owner.id, name="매장3")
    db.add(store)
    await db.flush()

    group = Group(
        public_id="hold_tst_001",
        store_id=store.id,
        product_name="홀드상품",
        price=8000,
        closes_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(group)
    await db.flush()

    hold1 = InventoryHold(
        group_id=group.id,
        user_id=user.id,
        quantity=1,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        status="active",
    )
    db.add(hold1)
    await db.flush()

    hold2 = InventoryHold(
        group_id=group.id,
        user_id=user.id,
        quantity=2,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        status="active",
    )
    db.add(hold2)

    with pytest.raises(IntegrityError):
        await db.flush()


async def test_check_constraints(db):
    """잘못된 status 값 CHECK 제약 위반."""
    user = User(kakao_id="test_kakao_010", role="invalid_role")
    db.add(user)

    with pytest.raises(IntegrityError):
        await db.flush()
