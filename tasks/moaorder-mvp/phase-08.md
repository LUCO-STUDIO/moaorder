# Phase 8: 상태 전이 + 피킹 + 수령

## 목표
마감 → 피킹 → 수령가능 → 완료 전체 사장님 운영 흐름 동작.

## 컨텍스트
- 설계 문서: `docs/flow.md` (마감→피킹→수령→완료, 상태 머신, 공구-주문 대응)
- 설계 문서: `docs/data-schema.md` (groups status, orders status)
- 설계 문서: `docs/adr.md` (ADR-006 CONFIRMED/PREPARING 통합, ADR-019 수령 optional)
- Phase 6의 결제/주문, Phase 7의 취소

## 구현 항목

### 백엔드

#### 1. 주문 사장님 API (5개)
`apps/api/app/api/owner_orders.py`:
- `GET /api/groups/{group_id}/orders` — 공구별 주문 목록. CRM-lite 포함:
  - 각 주문자: 누적 주문 횟수, 누적 구매 수량, 최근 주문일, 단골 여부 (5회 이상)
- `GET /api/groups/{group_id}/picking-list` — 피킹 리스트:
  - 총 수량 (상품명 + 총 수량)
  - 주문자별 목록 (이름, 수량, 픽업 시간대, 수령 여부)
  - 픽업형: 시간대별 그룹핑
- `POST /api/orders/{order_id}/approve-cancel` — 취소 요청 승인 → 환불 + 피킹 리스트 갱신
- `POST /api/orders/{order_id}/reject-cancel` — 취소 요청 거절 → 고객 알림
- `POST /api/orders/{order_id}/mark-picked-up` — 수령 완료 체크

#### 2. 상태 전이 로직 완성
`apps/api/app/services/group.py` 확장:
- `close_group(group_id)`:
  - groups.status → closed, closed_at 설정
  - 모든 PAID 주문 → CONFIRMED 일괄 전이
  - 공동구매형: min_quantity 체크 → 미달 시 전체 취소 + 환불 + 고객 알림, groups.status → cancelled
  - 피킹 리스트 자동 생성 (데이터 상으로는 orders 집계)
  - 고객 알림: "주문이 확정됐어요" 또는 "최소 수량 미달로 취소됐어요"
  - 사장님 알림: "피킹 리스트 준비됨" 또는 "미달 취소"
- `set_pickup_ready(group_id)`:
  - groups.status → pickup_ready
  - 모든 CONFIRMED 주문 → PICKUP_READY
  - 고객 알림: "수령 가능해요 + 픽업 안내"
- `complete_group(group_id)`:
  - groups.status → completed
  - 수령 체크된 주문 → PICKED_UP
  - 미체크 주문 → NOT_PICKED_UP
  - 고객 알림: "수령이 확인됐어요" (PICKED_UP) / 없음 (NOT_PICKED_UP)

#### 3. Pydantic 스키마
- `apps/api/app/schemas/picking.py` — PickingListResponse, PickingItem
- `apps/api/app/schemas/order.py` 확장: CRM-lite 필드 (total_order_count, total_quantity, last_order_date, is_regular)

### 프론트엔드

#### 4. 피킹 리스트
- `apps/web/src/routes/(owner)/groups/[groupId]/picking/+page.svelte`:
  - 총 수량 표시
  - 주문자별 목록 (이름, 수량, 픽업 시간대)
  - 고객별 수령 완료 체크 (optional, 탭으로 빠르게)
  - 미수령만 보기 필터
  - 주문자 검색
  - "공구 전체 완료" 버튼 (primary, 하단 고정)

#### 5. 취소 요청 처리
- 사장님 공구 상세 내 취소 요청 카드:
  - 주문자명, 수량, 요청 사유
  - 승인/거절 버튼

#### 6. 공구 상태 변경 UI
- 사장님 공구 상세 업데이트:
  - OPEN → "조기 마감" 버튼
  - CLOSED → "수령 가능" 버튼
  - PICKUP_READY → "공구 전체 완료" 버튼

#### 7. 마감/완료 공구 접근
- 공개 공구 상세 (Phase 4):
  - 마감: "종료된 공구예요" + CTA 비활성 + "이 매장의 진행 중 공구 보기"
  - 취소: "최소 수량 미달로 취소된 공구예요"
  - 완료: "종료된 공구예요"

### 테스트
- `apps/api/tests/test_state_transitions.py`:
  - close: PAID → CONFIRMED 일괄 전이
  - close (공동구매형 미달): 전체 CANCELLED + 환불
  - pickup_ready: CONFIRMED → PICKUP_READY
  - complete: 체크된 → PICKED_UP, 미체크 → NOT_PICKED_UP
  - approve-cancel → 환불 + 피킹 갱신
  - reject-cancel → 고객 알림

## 검증
```bash
cd apps/api && pytest tests/test_state_transitions.py -v
cd apps/web && npm run build

# 통합 (수동): 공구 생성 → 주문 → 조기 마감 → 피킹 → 수령가능 → 수령체크 → 전체 완료
```
