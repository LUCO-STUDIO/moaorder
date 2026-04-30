# Phase 5: 홈 + 대시보드

## 목표
고객 홈과 사장님 대시보드가 동작하여 공구/주문 현황을 확인 가능.

## 컨텍스트
- 설계 문서: `docs/flow.md` (고객 홈 구성, 사장님 대시보드)
- 설계 문서: `docs/code-architecture.md` (대시보드 API 2개, 고객 홈 API 3개)
- Phase 4의 공구 데이터 사용

## 구현 항목

### 백엔드

#### 1. 대시보드 API
`apps/api/app/api/dashboard.py`:
- `GET /api/dashboard/summary` — 오늘 진행 중 공구 수, 총 주문 수, 예상 매출, 마감 임박 공구
- `GET /api/dashboard/alerts` — 피킹 리스트 준비된 공구, 취소 요청 건수

#### 2. 고객 홈 API
`apps/api/app/api/home.py`:
- `GET /api/home/today-pickup` — 내 주문 중 오늘 수령 예정 (PICKUP_READY 이상 + CLOSED 상태 "준비중")
- `GET /api/home/feed` — 구독 매장 공구 피드 (status=open, 품절 제외, 마감 임박순, 동률 시 최신순)
- `GET /api/home/my-orders-active` — 진행 중 주문 상태

#### 3. Pydantic 스키마
- `apps/api/app/schemas/dashboard.py` — DashboardSummary, DashboardAlert
- `apps/api/app/schemas/home.py` — TodayPickupItem, FeedItem, ActiveOrderItem

### 프론트엔드

#### 4. 사장님 대시보드
- `apps/web/src/routes/(owner)/dashboard/+page.svelte`:
  - 오늘 진행 중 공구 수, 총 주문/매출
  - 공구 카드 리스트 (마감 임박순, 각 카드: 주문 수, 잔여 수량, 마감까지 남은 시간)
  - "피킹 리스트 확인" / "취소 요청 n건" 알림 카드
  - 공구 0개: "새 공구를 만들어보세요" 빈 상태 + FAB 강조
  - 10초 폴링으로 자동 갱신

#### 5. 사장님 공구 관리
- `apps/web/src/routes/(owner)/groups/+page.svelte`:
  - 전체 공구 목록 (상태 필터: 전체/진행중/마감됨/완료/취소)
  - 페이지네이션

#### 6. 고객 홈
- `apps/web/src/routes/(customer)/home/+page.svelte`:
  - [상단] 오늘 수령 예정 (없으면 숨김). 탭 → 주문 상세
  - [중단] 진행 중 주문 상태
  - [하단] 구독 매장 공구 피드 (마감 임박순)

### 테스트
- `apps/api/tests/test_dashboard.py`:
  - 공구 생성 → dashboard/summary에 반영 확인
  - 마감된 공구 → alerts에 피킹 리스트 카드 확인
- `apps/api/tests/test_home.py`:
  - 구독 매장 공구 → feed에 노출
  - 비구독 매장 공구 → 미노출

## 검증
```bash
cd apps/api && pytest tests/test_dashboard.py tests/test_home.py -v
cd apps/web && npm run build
```
