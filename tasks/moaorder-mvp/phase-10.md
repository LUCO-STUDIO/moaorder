# Phase 10: Worker + 이메일 발송

## 목표
백그라운드 워커가 동작하여 자동 마감, 알림 이메일 발송, 재고 선점 만료 처리가 자동으로 실행됨.

## 컨텍스트
- 설계 문서: `docs/code-architecture.md` (Worker 구조, DB 폴링, 1분 간격)
- 설계 문서: `docs/adr.md` (ADR-008 API/Worker 분리, ADR-009 DB 폴링)
- Phase 9의 notifications 데이터 사용
- Resend API: RESEND_API_KEY, EMAIL_FROM, EMAIL_REPLY_TO 환경변수

## 구현 항목

### 1. Worker 메인 루프
`apps/api/app/workers/main.py`:
```python
# 진입점: python -m app.workers.main
while True:
    process_auto_close()
    process_notifications()
    process_expired_holds()
    process_expired_idempotency()
    sleep(60)
```

### 2. 자동 마감 처리
`apps/api/app/workers/auto_close.py`:
- `process_auto_close()`:
  - `SELECT * FROM groups WHERE status = 'open' AND closes_at <= now()`
  - 각 공구에 대해 `close_group()` 호출 (Phase 8의 상태 전이 로직)
  - 에러 시 로그 + 다음 공구 계속 처리

### 3. 알림 발송 처리
`apps/api/app/workers/notification_sender.py`:
- `process_notifications()`:
  - `SELECT * FROM notifications WHERE status = 'pending' AND scheduled_at <= now() LIMIT 100`
  - 채널별 발송:
    - `inapp`: status → sent, sent_at 설정 (이미 DB에 있으므로 상태만 변경)
    - `email`: Resend API 호출 → 성공 시 sent, 실패 시 failed + error_message

### 4. Resend 이메일 연동
`apps/api/app/services/email.py`:
- Resend SDK 연동
- `send_email(to, subject, html_body)`:
  - resend.Emails.send() 호출
  - FROM: 환경변수 EMAIL_FROM
  - REPLY_TO: 환경변수 EMAIL_REPLY_TO
- 이메일 템플릿 (간단한 HTML):
  - 주문 확정, 취소, 수령 가능 등 알림별 제목/내용
  - 딥링크 URL 포함

### 5. 알림 이메일 생성 로직
Phase 9에서 인앱 알림만 생성했다면, 핵심 알림에 이메일 채널도 추가:
- 주문 확정 (마감 성공)
- 수령 가능
- 취소 승인/거절
- 공동구매형 미달 취소

각 알림 이벤트 발생 시 `inapp` + `email` 두 건의 notification 생성.
(사용자 이메일은 카카오에서 받은 이메일 사용, 없으면 인앱만)

### 6. 재고 선점 만료 처리
`apps/api/app/workers/hold_cleaner.py`:
- `process_expired_holds()`:
  - `SELECT * FROM inventory_holds WHERE status = 'active' AND expires_at <= now()`
  - 각 hold: status → expired + remaining_qty 복원 (단일 트랜잭션)

### 7. Idempotency 키 정리
`apps/api/app/workers/idempotency_cleaner.py`:
- `process_expired_idempotency()`:
  - `DELETE FROM idempotency_keys WHERE expires_at <= now()`

### 8. 로깅
- 각 워커 함수에 구조화된 로그:
  - `[auto_close] Closed group {group_id}, {n} orders confirmed`
  - `[notification] Sent {channel} to user {user_id}: {type}`
  - `[hold_cleaner] Expired {n} holds, restored qty`
  - `[error] {function}: {error_message}`

### 테스트
- `apps/api/tests/test_workers.py`:
  - 자동 마감: closes_at 지난 OPEN 공구 → CLOSED + 주문 CONFIRMED
  - 공동구매형 미달 자동 취소 → CANCELLED + 환불
  - 알림 발송: pending → sent (inapp)
  - 이메일 발송: Resend mock → sent + provider_message_id
  - hold 만료: active + expires_at 지남 → expired + remaining_qty 복원
  - idempotency 정리: 만료된 키 삭제

## 검증
```bash
cd apps/api && pytest tests/test_workers.py -v

# 워커 실행 (수동)
cd apps/api && python -m app.workers.main
# → 로그 출력 확인 (1분 간격으로 처리)

# 통합
# 1. 공구 생성 (마감 1분 후) → 워커가 자동 마감 → 주문 CONFIRMED 전이
# 2. 알림 생성 → 워커가 이메일 발송
```
