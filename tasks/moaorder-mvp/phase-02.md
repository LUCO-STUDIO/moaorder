# Phase 2: DB 스키마 + 핵심 모델

## 목표
12개 테이블이 PostgreSQL에 생성되고, SQLAlchemy 모델 + Pydantic 스키마로 접근 가능.

## 컨텍스트
- 설계 문서: `docs/data-schema.md` (전체 DDL, 인덱스, 제약조건)
- 설계 문서: `docs/adr.md` (ADR-003 공구=상품1:1, ADR-005 주문/환불 분리, ADR-014 User:Store 1:N)
- Phase 1에서 생성된 `apps/api/app/core/database.py`의 async engine 사용

## 구현 항목

### 1. SQLAlchemy 모델 (12개 테이블)
`apps/api/app/models/` 에 각 모델 파일 생성:

- `apps/api/app/models/base.py` — Base, 공통 mixin (id UUID, created_at, updated_at)
- `apps/api/app/models/user.py` — users 테이블
- `apps/api/app/models/store.py` — stores, store_members 테이블
- `apps/api/app/models/subscription.py` — subscriptions 테이블
- `apps/api/app/models/group.py` — groups, group_pickup_slots 테이블
- `apps/api/app/models/order.py` — orders, order_adjustments, order_events 테이블
- `apps/api/app/models/notification.py` — notifications 테이블
- `apps/api/app/models/inventory.py` — inventory_holds 테이블
- `apps/api/app/models/idempotency.py` — idempotency_keys 테이블
- `apps/api/app/models/__init__.py` — 전체 모델 import

**핵심 제약조건 (반드시 포함):**
- `groups.public_id`: VARCHAR(12) UNIQUE NOT NULL
- `orders`: UNIQUE INDEX on (group_id, user_id) WHERE status IN ('paid','confirmed','pickup_ready')
- `orders.payment_id`: UNIQUE INDEX WHERE payment_id IS NOT NULL
- `inventory_holds`: UNIQUE INDEX on (user_id, group_id) WHERE status = 'active'
- `inventory_holds.portone_payment_id`: UNIQUE INDEX WHERE NOT NULL
- `notifications.dedupe_key`: UNIQUE INDEX WHERE dedupe_key IS NOT NULL AND status != 'cancelled'
- `subscriptions`: UNIQUE(user_id, store_id)
- 모든 CHECK 제약 (status enum 값들)
- 모든 partial index (`docs/data-schema.md` 참조)

### 2. Alembic 설정
- `alembic init apps/api/alembic`
- `alembic.ini` 수정: sqlalchemy.url을 env에서 로드
- `alembic/env.py` 수정: async 지원 + 모든 모델 import
- 첫 마이그레이션 생성: `alembic revision --autogenerate -m "initial schema"`
- 마이그레이션 적용: `alembic upgrade head`

### 3. Pydantic 공통 스키마
`apps/api/app/schemas/common.py` 확장:
- `PaginationParams(page: int = 1, limit: int = 20)` — dependency
- `PaginatedResponse[T](items: list[T], total: int, page: int, limit: int)`
- 각 enum을 Python Enum으로 정의:
  - `UserRole`, `GroupStatus`, `GroupType`, `OrderStatus`, `AdjustmentType`, `RefundStatus`, `NotificationChannel`, `NotificationStatus`, `HoldStatus`

### 4. 테스트
- `apps/api/tests/test_models.py`:
  - DB 연결 테스트
  - 모든 테이블 생성 확인
  - User 생성 → Store 생성 → Group 생성 기본 CRUD
  - partial unique index 동작 확인 (같은 group_id+user_id로 active 주문 2개 생성 시도 → 에러)

## 검증
```bash
cd apps/api

# 1. 마이그레이션 적용
alembic upgrade head
# → 12개 테이블 생성

# 2. 테이블 확인
python -c "
import asyncio
from sqlalchemy import text
from app.core.database import engine
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\"))
        tables = [r[0] for r in result]
        print(f'Tables: {len(tables)}')
        for t in sorted(tables): print(f'  - {t}')
asyncio.run(check())
"
# → Tables: 12 (+ alembic_version)

# 3. 테스트 실행
pytest tests/test_models.py -v
```
