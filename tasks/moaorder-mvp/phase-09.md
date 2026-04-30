# Phase 9: 인앱 알림 + API

## 목표
모든 상태 전이에서 알림이 생성되고, 고객/사장님이 알림 목록을 확인 가능.

## 컨텍스트
- 설계 문서: `docs/flow.md` (상태 전이 알림 매핑 테이블)
- 설계 문서: `docs/data-schema.md` (notifications DDL, dedupe_key, status)
- 설계 문서: `docs/adr.md` (ADR-009 DB 폴링 단일 테이블, ADR-024 인앱+이메일)
- Phase 3~8에서 생성된 상태 전이 로직에 알림 생성을 연결

## 구현 항목

### 백엔드

#### 1. 알림 API (4개)
`apps/api/app/api/notifications.py`:
- `GET /api/notifications` — 알림 목록 (페이지네이션, 최신순, status=sent or pending)
- `POST /api/notifications/{id}/read` — 읽음 처리 (read_at 설정)
- `POST /api/notifications/read-all` — 전체 읽음
- `GET /api/notifications/unread-count` — 읽지 않은 알림 수

#### 2. 알림 생성 서비스 완성
`apps/api/app/services/notification.py` 확장:
이전 phase들에서 기본 구조만 잡아놨던 알림 생성 로직을 완성.

모든 상태 전이에 알림 연결:
- **공구 게시** → 구독 고객 전원: "○○ 매장에서 새 공구가 열렸어요"
- **마감 (성공)** → 주문자: "주문이 확정됐어요" / 사장님: "피킹 리스트 준비됨"
- **마감 (미달)** → 주문자: "최소 수량 미달로 취소됐어요, 환불 예정" / 사장님: "미달 취소"
- **수령가능** → 주문자: "수령 가능해요, 매장에서 수령해주세요"
- **고객 취소 (마감전)** → 사장님: "○○님 주문 취소됨"
- **취소 요청 (마감후)** → 사장님: "취소 요청 확인 필요"
- **취소 승인** → 고객: "취소가 승인됐어요, 환불 예정"
- **취소 거절** → 고객: "취소 요청이 거절됐어요"
- **수령 완료** → 고객: "수령이 확인됐어요"
- **공구 수정 (중요 필드)** → 주문자: "공구 정보가 변경됐어요"

각 알림:
- type 설정 (예: 'group_opened', 'order_confirmed', 'cancel_approved' 등)
- dedupe_key 설정 (중복 방지)
- title + body 한국어 메시지
- payload에 딥링크용 정보 (group_id, order_id 등)
- 즉시 발송 알림: scheduled_at = now()

#### 3. 알림 취소 규칙
- 주문 취소 시: 해당 주문의 미발송 알림 전부 cancelled
- 픽업 시간 변경 시: 기존 리마인더 알림 cancelled → 새 시간으로 재생성
- 공구 취소 시: 해당 공구 관련 미발송 알림 전부 cancelled

#### 4. 픽업 리마인더 스케줄링
- 픽업형 주문 생성 시: `scheduled_at = pickup_start - 30분` 알림 생성
  - 고객: "곧 픽업 시간이에요 (○시 ○분)"
  - 사장님: "○○님 픽업 예정 (상품명 N개)"
- 픽업형에만 적용, 시간대 선택된 주문만

#### 5. Pydantic 스키마
- `apps/api/app/schemas/notification.py` — NotificationResponse, NotificationListResponse, UnreadCountResponse

### 프론트엔드

#### 6. 알림 목록
- `apps/web/src/routes/(customer)/notifications/+page.svelte` — 고객 알림 목록
- `apps/web/src/routes/(owner)/notifications/+page.svelte` — 사장님 알림 목록
- 공통 알림 카드 컴포넌트:
  - 아이콘 (타입별 다르게)
  - 제목 + 본문
  - 시간 (상대 시간: "3분 전", "1시간 전")
  - 읽음/안읽음 스타일 구분
  - 탭 → 관련 화면으로 이동 (payload 기반)

#### 7. 미읽음 배지
- `apps/web/src/lib/stores/notifications.ts` — 미읽음 수 스토어
- BottomNav 알림 탭에 배지 표시
- 주기적 폴링 (30초 간격)

### 테스트
- `apps/api/tests/test_notifications.py`:
  - 공구 생성 → 구독 고객 알림 생성 확인
  - 마감 → 주문자 + 사장님 알림 확인
  - 주문 취소 → 관련 미발송 알림 cancelled
  - 알림 API: list, read, read-all, unread-count 동작 확인
  - dedupe_key 중복 시 생성 안 됨

## 검증
```bash
cd apps/api && pytest tests/test_notifications.py -v
cd apps/web && npm run build
```
