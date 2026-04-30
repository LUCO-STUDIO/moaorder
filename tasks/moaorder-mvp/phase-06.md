# Phase 6: 결제 + 재고 선점

## 목표
고객이 공구에서 결제하고 주문이 생성됨. 재고 선점 → 결제 → 웹훅 확정 전체 흐름 동작.

## 컨텍스트
- 설계 문서: `docs/code-architecture.md` (결제 흐름, 동시성 처리, checkout/prepare → webhook → by-payment)
- 설계 문서: `docs/data-schema.md` (orders, inventory_holds, idempotency_keys DDL)
- 설계 문서: `docs/adr.md` (ADR-007 재고 선점→결제→웹훅, ADR-021 Idempotency)
- Phase 4의 공구 데이터, Phase 3의 인증 사용
- PortOne V2 API: 테스트 채널 (토스페이먼츠) 사용
  - 환경변수: PORTONE_STORE_ID, PORTONE_API_SECRET, PORTONE_CHANNEL_KEY

## 구현 항목

### 백엔드

#### 1. Checkout API
`apps/api/app/api/checkout.py`:
- `POST /api/checkout/prepare`:
  - body: { group_id, quantity, pickup_slot_id? }
  - 기존 active hold 조회 (user_id + group_id)
    - 수량 동일: expires_at 갱신, 기존 hold 반환
    - 수량 다름: 기존 hold expired + remaining_qty 복원 + 새 hold
    - 없음: 새 hold
  - 단일 트랜잭션: remaining_qty 차감 (`UPDATE ... WHERE remaining_qty >= n`) + hold 생성
  - 실패 시 SoldOutError
  - PortOne 결제 준비: payment_id 생성 (UUID), hold에 portone_payment_id 저장
  - 응답: { hold_id, payment_id, store_id, amount, order_name }

#### 2. Webhook API
`apps/api/app/api/webhooks.py`:
- `POST /api/webhooks/portone`:
  - PortOne 서명 검증
  - PortOne API로 결제 상태 조회 (httpx)
  - 금액/상태 일치 확인
  - idempotency: payment_id 기준 중복 체크 (orders.payment_id UNIQUE)
  - 주문 생성: status=PAID, quantity, total_amount, current_quantity=quantity, current_amount=total_amount
  - hold → converted
  - order_events 기록 (payment_completed)
  - 첫 주문 시 자동 구독 생성 (subscriptions INSERT ... ON CONFLICT DO NOTHING)
  - 응답: 200

#### 3. 결제 확인 API
`apps/api/app/api/checkout.py`:
- `GET /api/orders/by-payment/{payment_id}`:
  - 주문 있음: 200 { order_id, status }
  - hold 있지만 주문 미생성: 200 { status: "processing" }
  - 없음: 404

#### 4. 서비스 레이어
- `apps/api/app/services/checkout.py` — prepare 로직, hold 관리
- `apps/api/app/services/payment.py` — PortOne API 호출 (결제 조회, 서명 검증)
- `apps/api/app/services/idempotency.py` — idempotency key 관리

#### 5. Pydantic 스키마
- `apps/api/app/schemas/checkout.py` — CheckoutPrepareRequest, CheckoutPrepareResponse, PaymentStatusResponse
- `apps/api/app/schemas/order.py` — OrderResponse, OrderListResponse

### 프론트엔드

#### 6. 주문/결제 화면
- `apps/web/src/routes/g/[publicId]/order/+page.svelte`:
  - 수량 선택 (잔여 수량 내에서)
  - 픽업형: 시간대 선택 (radio)
  - 결제 금액 합계 표시
  - "결제하기" CTA → checkout/prepare API → PortOne SDK 결제창 호출

#### 7. PortOne SDK 연동
- `apps/web/src/lib/payment.ts`:
  - PortOne V2 Browser SDK 로드
  - `requestPayment()` 호출 (storeId, channelKey, paymentId, orderName, totalAmount, payMethod)
  - 결제 완료 리다이렉트 → 확인 페이지

#### 8. 결제 확인 + 주문 완료
- `apps/web/src/routes/g/[publicId]/order/complete/+page.svelte`:
  - paymentId를 query param으로 수신 (`?paymentId=xxx`)
  - "주문 확인 중" UI 표시
  - GET /api/orders/by-payment/{paymentId} 폴링 (2초 간격, 최대 30초)
  - 주문 생성됨 → 주문 완료 화면 (주문 요약 + 자동 구독 안내)
  - 30초 초과 → "주문내역에서 확인해주세요" 안내

### 테스트
- `apps/api/tests/test_checkout.py`:
  - prepare → remaining_qty 차감 + hold 생성 확인
  - 동시 2건 prepare → 재고 부족 시 하나만 성공
  - prepare 재호출 (수량 동일) → 같은 hold 반환
  - prepare 재호출 (수량 다름) → 기존 복원 + 새 hold
  - 웹훅 mock → 주문 생성 확인 + hold converted
  - 웹훅 중복 호출 → 주문 중복 생성 안 됨 (UNIQUE 제약)
  - by-payment: 주문 있으면 200, 처리중이면 processing, 없으면 404
  - 자동 구독 생성 확인

## 검증
```bash
cd apps/api && pytest tests/test_checkout.py -v

# 프론트 빌드
cd apps/web && npm run build

# 통합 (수동 — PortOne 테스트 채널)
# 1. 공구 생성 → 공개 링크 → 주문하기 → 결제창 → 테스트 결제 → 주문 완료
```
