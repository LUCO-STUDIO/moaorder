# Phase 7: 주문 변경 + 취소

## 목표
고객이 마감 전 수량 줄이기/취소, 마감 후 취소 요청 가능. 환불 처리 동작.

## 컨텍스트
- 설계 문서: `docs/flow.md` (주문 변경/취소 흐름, 취소 가능 범위)
- 설계 문서: `docs/data-schema.md` (orders, order_adjustments, order_events DDL)
- 설계 문서: `docs/adr.md` (ADR-005 주문/환불 분리, ADR-020 수량 줄이기만)
- Phase 6의 주문 데이터 사용

## 구현 항목

### 백엔드

#### 1. 주문 고객 API (5개)
`apps/api/app/api/orders.py`:
- `GET /api/orders/my` — 내 주문 목록 (진행중/완료 구분, 페이지네이션)
- `GET /api/orders/{order_id}` — 주문 상세 (order_events로 상태 타임라인 포함)
- `POST /api/orders/{order_id}/reduce` — 수량 줄이기 (마감 전만):
  - body: { quantity_after }
  - current_quantity 업데이트
  - 차액 계산 → PortOne 부분환불 API 호출
  - order_adjustments 생성 (type=quantity_reduce)
  - order_events 기록
  - remaining_qty 복원 (차감된 수량만큼)
- `POST /api/orders/{order_id}/cancel` — 전체 취소 (마감 전만):
  - status → cancelled
  - PortOne 전액환불
  - order_adjustments 생성 (type=full_cancel)
  - remaining_qty 복원
- `POST /api/orders/{order_id}/cancel-request` — 취소 요청 (마감 후, CONFIRMED까지만):
  - cancel_requested_at 설정
  - pending 취소 요청 1건만 허용 (이미 있으면 409)
  - 사장님에게 알림 생성

#### 2. 환불 서비스
- `apps/api/app/services/refund.py`:
  - `process_partial_refund(order, refund_amount)` — PortOne 부분취소 API
  - `process_full_refund(order)` — PortOne 전액취소 API
  - 환불 결과 → order_adjustments.refund_status 업데이트
  - order_adjustments.refund_payment_id 저장

#### 3. Pydantic 스키마
- `apps/api/app/schemas/order.py` 확장:
  - OrderDetailResponse (상태 타임라인 포함)
  - ReduceRequest, CancelRequestBody

### 프론트엔드

#### 4. 주문내역
- `apps/web/src/routes/(customer)/orders/+page.svelte` — 진행중/완료 탭, 주문 카드 리스트
- `apps/web/src/routes/(customer)/orders/[orderId]/+page.svelte` — 주문 상세:
  - 주문 요약 (공구명, 상품, 수량, 결제금액)
  - 상태 타임라인 (order_events 기반)
  - 픽업형: 선택한 픽업 시간대
  - 마감 전: 수량 줄이기 / 전체 취소 버튼
  - 마감 후: 취소 요청 버튼 (사장님 승인 필요 안내)
  - 수량 늘리기 → "새로 주문해주세요" 안내
  - 수령가능 시: 픽업 안내 상단 강조
  - 고객 라벨 + 서브텍스트 표시

### 테스트
- `apps/api/tests/test_orders.py`:
  - 수량 줄이기 → current_quantity 변경 + adjustment 생성 + remaining_qty 복원
  - 전체 취소 → status=cancelled + adjustment + remaining_qty 복원
  - 마감 후 reduce 시도 → 에러
  - 취소 요청 → cancel_requested_at 설정 + 사장님 알림
  - 중복 취소 요청 → 409

## 검증
```bash
cd apps/api && pytest tests/test_orders.py -v
cd apps/web && npm run build
```
