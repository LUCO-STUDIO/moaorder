# 모아오더 코드 아키텍처

## 시스템 구성

```
[브라우저] ←→ [SvelteKit @ Vercel 서울]
                    ↓ SSR / 클라이언트 직접 호출
              [FastAPI @ Railway 도쿄]
                    ↓
              [PostgreSQL @ Railway]

[Worker @ Railway] — 별도 프로세스, 같은 코드베이스
[PortOne] → 웹훅 → [FastAPI]
[Cloudflare R2] ← Presigned URL 업로드
[SMS/Email Provider] ← Worker 발송
```

## 기술 스택

| 영역 | 선택 | 비고 |
|------|------|------|
| Frontend | SvelteKit | SSR + CSR 혼합 |
| Backend | FastAPI (async) | Python |
| DB | PostgreSQL | TIMESTAMPTZ, JSONB |
| ORM | SQLAlchemy 2.0 + Alembic | async, 마이그레이션 |
| Auth | 카카오 OAuth → JWT | 단일 토큰 7일 |
| 결제 | PortOne v2 | 카카오페이 + 카드 |
| 이미지 | Cloudflare R2 | Presigned URL |
| 배포 | Vercel + Railway | 월 $5~10 |

## 모노레포 구조

```
moaorder/
├── apps/
│   ├── web/                    # SvelteKit
│   │   ├── src/
│   │   │   ├── routes/         # 페이지 라우트
│   │   │   ├── lib/            # API 클라이언트, 스토어, 유틸
│   │   │   └── components/     # UI 컴포넌트
│   │   └── static/
│   └── api/                    # FastAPI + Worker
│       ├── app/
│       │   ├── api/            # 라우터 (엔드포인트)
│       │   ├── models/         # SQLAlchemy 모델
│       │   ├── schemas/        # Pydantic 스키마 (입력 검증 단일 진실원천)
│       │   ├── services/       # 비즈니스 로직
│       │   ├── workers/        # 워커 진입점 + 잡
│       │   └── core/           # config, auth, db, middleware
│       ├── alembic/            # DB 마이그레이션
│       └── tests/
├── docs/                       # 설계 문서
├── docker-compose.yml          # 로컬 PostgreSQL
└── README.md
```

## 렌더링 전략

- **SSR**: 공구 상세 (OG 태그, 카카오 미리보기), 공개 페이지
- **CSR**: 주문/결제, 대시보드, 알림 등 인터랙션 중심 화면
- SvelteKit `load` 함수에서 FastAPI 서버사이드 호출 (SSR)
- 브라우저에서 FastAPI 직접 호출 (CSR 인터랙션)

## 인증

```
카카오 OAuth → SvelteKit callback → POST /api/auth/kakao/exchange → JWT 발급
```

- 단일 JWT 7일, httpOnly + secure + sameSite=lax 쿠키
- domain: `.moaorder.com`
- 권한: FastAPI dependency로 분리

```python
@router.get("/groups/{group_id}")                              # 공개
@router.get("/orders/my", dependencies=[Depends(require_auth)])  # 로그인 필수
@router.post("/groups", dependencies=[Depends(require_owner)])   # 사장님 전용
```

## 결제 흐름

```
1. POST /api/checkout/prepare
   → 트랜잭션: remaining_qty 차감 + inventory_hold 생성 (TTL 10분)
   → 응답: hold_id, portone_payment_id

2. 클라이언트: PortOne 결제창 호출

3. POST /api/webhooks/portone (PortOne → 서버)
   → 서명 검증 + PortOne API로 결제 상태 조회
   → 금액/상태 일치 확인
   → 주문 생성 (status=PAID) + hold → converted
   → 자동 구독 생성 (첫 주문 시)

4. 클라이언트: GET /api/orders/by-payment/{payment_id} 폴링 (2초 간격, 최대 30초)
   → 200 { order_id, status } 또는 200 { status: "processing" }
   → 30초 초과: "주문내역에서 확인해주세요" 안내
```

프론트 리다이렉트 절대 불신뢰. 웹훅 + 서버 검증이 최종.

## 동시성 처리

재고 차감: 낙관적 동시성 + 원자적 조건부 UPDATE.

```python
async with db.begin():
    result = await db.execute(
        update(groups)
        .where(groups.c.id == group_id, groups.c.remaining_qty >= quantity)
        .values(remaining_qty=groups.c.remaining_qty - quantity)
        .returning(groups.c.remaining_qty)
    )
    if result.rowcount == 0:
        raise SoldOutError()
    hold = InventoryHold(...)
    db.add(hold)
```

## Worker

API와 같은 코드베이스, 진입점만 분리. Redis/Celery 없음.

```bash
# API
uvicorn app.main:app
# Worker
python -m app.workers.main
```

```python
# workers/main.py
while True:
    process_auto_close()        # closes_at 지난 OPEN 공구 마감
    process_notifications()     # pending + scheduled_at <= now 발송
    process_expired_holds()     # 10분 만료 hold → remaining_qty 복원
    process_expired_idempotency()  # TTL 만료 키 정리
    sleep(60)
```

Railway에서 api 서비스 + worker 서비스 2개로 배포.

## API 개요 (45개)

```
인증 (3)          POST auth/kakao/exchange, POST auth/logout, GET auth/me
온보딩 (2)        POST onboarding/owner, POST onboarding/customer
사용자 (1)        PATCH users/me
매장 (2)          GET stores/{id}, PATCH stores/{id}
구독 (3)          POST subscriptions, DELETE subscriptions/stores/{id}, GET subscriptions/my
공구 공개 (2)     GET public/groups/{public_id}, GET public/stores/{id}/groups
공구 사장님 (7)   POST groups, PATCH groups/{id}, DELETE groups/{id},
                  POST groups/{id}/close, POST groups/{id}/pickup-ready,
                  POST groups/{id}/complete, GET groups/my
결제 (3)          POST checkout/prepare, POST webhooks/portone, GET orders/by-payment/{id}
주문 고객 (5)     GET orders/my, GET orders/{id},
                  POST orders/{id}/reduce, POST orders/{id}/cancel,
                  POST orders/{id}/cancel-request
주문 사장님 (5)   GET groups/{id}/orders, GET groups/{id}/picking-list,
                  POST orders/{id}/approve-cancel, POST orders/{id}/reject-cancel,
                  POST orders/{id}/mark-picked-up
대시보드 (2)      GET dashboard/summary, GET dashboard/alerts
고객 홈 (3)       GET home/today-pickup, GET home/feed, GET home/my-orders-active
알림 (4)          GET notifications, POST notifications/{id}/read,
                  POST notifications/read-all, GET notifications/unread-count
이미지 (1)        POST uploads/presign
```

공개 API: `/api/public/*` 프리픽스. 인증 불요.
페이지네이션: offset 기반 (`?page=1&limit=20`).
공개/내부 응답: 같은 스키마, 민감 필드(주문자 상세, 매출, 취소 요청) 제외.

## 에러 응답

```json
{
  "error": {
    "code": "SOLD_OUT",
    "message": "품절되었습니다",
    "detail": null,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

request_id: FastAPI 미들웨어에서 생성. `X-Request-ID` 헤더 있으면 재사용.

## CORS

```python
origins = [
    "https://moaorder.com",
    "https://www.moaorder.com",
    "http://localhost:5173",
]
# credentials=True
```

## Rate Limiting

| 대상 | 제한 |
|------|------|
| 공개 API | 분당 60회 |
| 인증 | 분당 10회 |
| checkout/prepare | 분당 5회 |
| webhook | 서명 검증 + idempotency (rate limit 대신) |

## Timezone

- DB/API: UTC (TIMESTAMPTZ)
- 프론트 입력: KST → UTC 변환 후 전송
- 프론트 표시: UTC → KST 변환
- 워커: UTC 기준 비교

## 모바일 최적화

**필수:**
- iOS Safari 15+, Android Chrome 90+
- 이미지: 업로드 시 리사이징 (최대 1200px, webp)
- 첫 화면 로드 3초 이내 (3G)

**성능 예산 목표:**
- JS 번들 200KB 이하 (gzip)
- LCP 2.5초 이내

## 배포

| 서비스 | 플랫폼 | 도메인 |
|--------|--------|--------|
| SvelteKit | Vercel (서울) | moaorder.com |
| FastAPI | Railway (도쿄) | api.moaorder.com |
| Worker | Railway (도쿄) | — |
| PostgreSQL | Railway (도쿄) | — |
| 이미지 | Cloudflare R2 | — |

초기 비용: 월 $5~10.

## 로깅/모니터링

- 구조화된 stdout 로그 → Railway 대시보드
- Sentry: S1 완료 후 추가 (무료 티어)
- DB 백업: Railway 플랜 확인, 미지원 시 pg_dump 일 1회

## 테스트 전략

- 결제/환불 흐름: 통합 테스트 필수
- 재고 동시성: 유닛 테스트 필수
- 자동 마감 워커: 유닛 테스트 필수
- 나머지: 수동 테스트
