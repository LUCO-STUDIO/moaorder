# 모아오더 데이터 스키마

## 테이블 요약 (12개)

| 테이블 | 설명 | 레코드 특성 |
|--------|------|-------------|
| users | 사용자 | 천~만 |
| stores | 매장 | 소규모 |
| store_members | 매장-사용자 관계 | 소규모 |
| subscriptions | 구독 | 매장당 수십~수백 |
| groups | 공구 (=상품) | 매장당 일 수 건 |
| group_pickup_slots | 픽업 시간대 | 공구당 2~4개 |
| orders | 주문 | 공구당 수십 건 |
| order_adjustments | 주문 변경/취소 이력 | 주문의 10~20% |
| order_events | 주문 이벤트 로그 | append-only |
| notifications | 알림 (발송 큐 + 사용자 목록 겸용) | 가장 빠르게 증가 |
| inventory_holds | 재고 선점 | 결제 진행 중 건 |
| idempotency_keys | 중복 실행 방지 | TTL 기반 정리 |

## 핵심 설계 원칙

- 공구 1개 = 상품 1개 (별도 products 테이블 없음)
- User:Store = 1:N (스키마), MVP 정책은 1:1
- 주문 상태와 환불 상태 분리 (환불은 order_adjustments에서 관리)
- 모든 timestamp는 UTC (TIMESTAMPTZ)
- 이력성 데이터 삭제 불가 (orders, adjustments, events, notifications)

---

## DDL

### users

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kakao_id      VARCHAR(50) UNIQUE NOT NULL,
  role          VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'customer')),
  nickname      VARCHAR(50),
  phone         VARCHAR(20),
  region        VARCHAR(100),
  category      VARCHAR(100),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### stores

```sql
CREATE TABLE stores (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id      UUID NOT NULL REFERENCES users(id),
  name          VARCHAR(100) NOT NULL,
  region        VARCHAR(100),
  category      VARCHAR(100),
  contact       VARCHAR(50),
  notification_settings JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_stores_owner ON stores(owner_id);
```

### store_members

```sql
CREATE TABLE store_members (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id      UUID NOT NULL REFERENCES stores(id),
  user_id       UUID NOT NULL REFERENCES users(id),
  role          VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'staff')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(store_id, user_id)
);
```

### subscriptions

```sql
CREATE TABLE subscriptions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id),
  store_id      UUID NOT NULL REFERENCES stores(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  unsubscribed_at TIMESTAMPTZ,
  UNIQUE(user_id, store_id)
);
CREATE INDEX idx_subs_user ON subscriptions(user_id) WHERE unsubscribed_at IS NULL;
CREATE INDEX idx_subs_store ON subscriptions(store_id) WHERE unsubscribed_at IS NULL;
```

소프트 삭제: `unsubscribed_at` 설정. 첫 주문 완료 시 자동 생성.

### groups

```sql
CREATE TABLE groups (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  public_id       VARCHAR(12) UNIQUE NOT NULL,  -- nanoid, 공유 URL용
  store_id        UUID NOT NULL REFERENCES stores(id),
  status          VARCHAR(20) NOT NULL DEFAULT 'open'
                  CHECK (status IN ('open', 'closed', 'pickup_ready', 'completed', 'cancelled')),
  type            VARCHAR(20) NOT NULL DEFAULT 'reservation'
                  CHECK (type IN ('reservation', 'group_buy', 'pickup')),
  product_name    VARCHAR(200) NOT NULL,
  price           INTEGER NOT NULL,
  description     TEXT,
  image_url       VARCHAR(500),
  max_quantity    INTEGER,          -- NULL = 무제한
  remaining_qty   INTEGER,          -- NULL = 무제한, 생성 시 max_quantity로 초기화
  min_quantity    INTEGER,          -- 공동구매형 전용
  closes_at       TIMESTAMPTZ NOT NULL,
  closed_at       TIMESTAMPTZ,      -- 실제 마감 시각 (조기 마감 포함)
  cancel_reason   VARCHAR(200),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_groups_store_status ON groups(store_id, status);
CREATE INDEX idx_groups_closes_at ON groups(closes_at) WHERE status = 'open';
```

`remaining_qty`: 원자적 차감 대상 — `UPDATE ... WHERE remaining_qty >= n`.
주문 가능 조건: `status = 'open' AND closes_at > now() AND (remaining_qty > 0 OR remaining_qty IS NULL)`.
조건부 삭제: OPEN + 주문 0건 + active hold 0건일 때만.

### group_pickup_slots

```sql
CREATE TABLE group_pickup_slots (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id      UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  label         VARCHAR(100) NOT NULL,
  start_at      TIMESTAMPTZ NOT NULL,
  end_at        TIMESTAMPTZ NOT NULL,
  sort_order    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_pickup_slots_group ON group_pickup_slots(group_id);
```

픽업형 전용. 주문 연결된 슬롯은 수정/삭제 불가, 새 슬롯 추가만.

### orders

```sql
CREATE TABLE orders (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id              UUID NOT NULL REFERENCES groups(id),
  user_id               UUID NOT NULL REFERENCES users(id),
  store_id              UUID NOT NULL REFERENCES stores(id),  -- 비정규화 (조회 성능)
  status                VARCHAR(20) NOT NULL DEFAULT 'paid'
                        CHECK (status IN ('paid', 'confirmed', 'pickup_ready',
                                          'picked_up', 'not_picked_up', 'cancelled')),
  quantity              INTEGER NOT NULL,       -- 최초 (불변)
  total_amount          INTEGER NOT NULL,       -- 최초 (불변)
  current_quantity      INTEGER NOT NULL,       -- 부분취소 후 현재
  current_amount        INTEGER NOT NULL,       -- 부분취소 후 현재
  payment_id            VARCHAR(200),           -- 포트원 결제 ID
  paid_at               TIMESTAMPTZ,
  pickup_slot_id        UUID REFERENCES group_pickup_slots(id),
  cancel_requested_at   TIMESTAMPTZ,
  cancel_request_reason VARCHAR(200),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_group ON orders(group_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_store_status ON orders(store_id, status);
CREATE UNIQUE INDEX idx_orders_group_user_active ON orders(group_id, user_id)
  WHERE status IN ('paid', 'confirmed', 'pickup_ready');
CREATE UNIQUE INDEX idx_orders_payment ON orders(payment_id)
  WHERE payment_id IS NOT NULL;
```

활성 주문만 중복 차단 (취소/수령 완료/미수령 후 재주문 가능).

### order_adjustments

```sql
CREATE TABLE order_adjustments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id          UUID NOT NULL REFERENCES orders(id),
  type              VARCHAR(30) NOT NULL
                    CHECK (type IN ('quantity_reduce', 'full_cancel', 'admin_cancel', 'system_cancel')),
  quantity_before   INTEGER NOT NULL,
  quantity_after    INTEGER NOT NULL,
  refund_amount     INTEGER NOT NULL,
  refund_status     VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (refund_status IN ('pending', 'completed', 'failed')),
  refund_payment_id VARCHAR(200),
  reason            VARCHAR(200),
  requested_by      VARCHAR(20) NOT NULL
                    CHECK (requested_by IN ('customer', 'owner', 'system')),
  approved_by       UUID REFERENCES users(id),
  approved_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_adjustments_order ON order_adjustments(order_id);
CREATE INDEX idx_adjustments_refund ON order_adjustments(refund_status)
  WHERE refund_status = 'pending';
```

### order_events

```sql
CREATE TABLE order_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id      UUID NOT NULL REFERENCES orders(id),
  event_type    VARCHAR(50) NOT NULL,
  actor_id      UUID REFERENCES users(id),
  actor_type    VARCHAR(20) CHECK (actor_type IN ('customer', 'owner', 'system')),
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_events_order ON order_events(order_id, created_at);
```

상태 타임라인 데이터 소스. 분쟁 대응용.

### notifications

```sql
CREATE TABLE notifications (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES users(id),
  store_id            UUID REFERENCES stores(id),
  group_id            UUID REFERENCES groups(id),
  order_id            UUID REFERENCES orders(id),
  type                VARCHAR(50) NOT NULL,
  channel             VARCHAR(20) NOT NULL DEFAULT 'inapp'
                      CHECK (channel IN ('inapp', 'sms', 'email')),
  status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
  title               VARCHAR(200) NOT NULL,
  body                TEXT,
  payload             JSONB DEFAULT '{}',
  dedupe_key          VARCHAR(200),
  scheduled_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at             TIMESTAMPTZ,
  failed_at           TIMESTAMPTZ,
  read_at             TIMESTAMPTZ,
  error_message       TEXT,
  provider_message_id VARCHAR(200),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notif_pending ON notifications(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_notif_user ON notifications(user_id, created_at DESC)
  WHERE status IN ('sent', 'pending');
CREATE UNIQUE INDEX idx_notif_dedupe ON notifications(dedupe_key)
  WHERE dedupe_key IS NOT NULL AND status != 'cancelled';
```

발송 큐 + 사용자 알림 목록 겸용. 워커가 1분 간격으로 `status=pending AND scheduled_at <= now()` 처리.
취소 시 기존 알림 `cancelled` → 새 알림 생성.

### inventory_holds

```sql
CREATE TABLE inventory_holds (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id            UUID NOT NULL REFERENCES groups(id),
  user_id             UUID NOT NULL REFERENCES users(id),
  quantity            INTEGER NOT NULL,
  portone_payment_id  VARCHAR(200),
  expires_at          TIMESTAMPTZ NOT NULL,  -- TTL 10분
  status              VARCHAR(20) NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'converted', 'expired')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_holds_expires ON inventory_holds(expires_at) WHERE status = 'active';
CREATE UNIQUE INDEX idx_holds_active_user_group ON inventory_holds(user_id, group_id)
  WHERE status = 'active';
CREATE UNIQUE INDEX idx_holds_payment ON inventory_holds(portone_payment_id)
  WHERE portone_payment_id IS NOT NULL;
```

재고 차감 + hold 생성은 단일 트랜잭션.
수량 변경 재호출: 기존 hold 해제 → 재고 복원 → 새 hold (단일 트랜잭션).

### idempotency_keys

```sql
CREATE TABLE idempotency_keys (
  key             VARCHAR(200) PRIMARY KEY,
  resource_type   VARCHAR(50) NOT NULL,
  resource_id     UUID,
  status_code     INTEGER NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);
```

| resource_type | TTL |
|---|---|
| hold / checkout | 24시간 |
| order / refund / webhook | 7일 |

---

## 삭제 정책

| 대상 | 정책 |
|------|------|
| orders, order_adjustments, order_events, notifications | 삭제 불가 |
| subscriptions | 소프트 삭제 (unsubscribed_at) |
| groups | OPEN + 주문 0건 + hold 0건일 때만 하드 삭제 |
| idempotency_keys | TTL 만료 후 워커가 정리 |
| users, stores | MVP에서 탈퇴 미지원 |
