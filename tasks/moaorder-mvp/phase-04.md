# Phase 4: 공구 CRUD + 공개 조회

## 목표
사장님이 공구를 생성/수정/삭제하고, 고객이 public_id로 공개 조회 가능. 이미지 업로드 동작.

## 컨텍스트
- 설계 문서: `docs/flow.md` (사장님 공구 생성 흐름, 고객 공구 상세)
- 설계 문서: `docs/data-schema.md` (groups, group_pickup_slots DDL)
- 설계 문서: `docs/code-architecture.md` (API 목록 — 공구 사장님 7개, 공구 공개 2개, 이미지 1개)
- 설계 문서: `docs/adr.md` (ADR-003 공구=상품1:1, ADR-015 public_id nanoid, ADR-012 Presigned URL, ADR-018 초안 제거)
- Phase 3의 인증/권한 dependency 사용

## 구현 항목

### 백엔드

#### 1. 공구 사장님 API (7개)
`apps/api/app/api/groups.py`:
- `POST /api/groups` — 공구 생성 (즉시 게시). nanoid로 public_id 생성. max_quantity 설정 시 remaining_qty 초기화. 픽업형이면 pickup_slots도 함께 생성. 구독 고객에게 알림 생성 (notifications 테이블에 insert).
- `PATCH /api/groups/{group_id}` — 공구 수정 (마감 전만). 수정 제한 규칙:
  - 가격 변경: OK (기존 주문 불변)
  - 타입 변경: 주문 있으면 불가
  - max_quantity: 현재 주문 수 이상으로만
  - 픽업 슬롯: 주문 연결된 슬롯 수정/삭제 불가, 새 슬롯 추가만
  - 마감시간/가격/픽업시간 변경 시 주문자 알림 생성
- `DELETE /api/groups/{group_id}` — OPEN + 주문 0건 + active hold 0건일 때만
- `POST /api/groups/{group_id}/close` — 조기 마감 (상태 전이 로직은 Phase 6b에서 완성)
- `POST /api/groups/{group_id}/pickup-ready` — 수령 가능 변경
- `POST /api/groups/{group_id}/complete` — 공구 전체 완료
- `GET /api/groups/my` — 내 매장 공구 목록 (?status=&page=&limit=)

#### 2. 공구 공개 API (2개)
`apps/api/app/api/public.py`:
- `GET /api/public/groups/{public_id}` — 공개 공구 상세 (인증 불요). SSR OG 태그용 데이터 포함.
- `GET /api/public/stores/{store_id}/groups` — 매장의 진행 중 공구 (?status=open&sort=closes_at)

#### 3. 이미지 업로드 API
`apps/api/app/api/uploads.py`:
- `POST /api/uploads/presign` — R2 Presigned URL 발급. boto3 S3 클라이언트로 R2 엔드포인트 호출.
- `apps/api/app/services/storage.py` — R2 presigned URL 생성 로직

#### 4. 서비스 레이어
- `apps/api/app/services/group.py` — 공구 CRUD 비즈니스 로직
- `apps/api/app/services/notification.py` — 알림 생성 헬퍼 (create_notification, 구독 고객 일괄 알림 등)

#### 5. Pydantic 스키마
- `apps/api/app/schemas/group.py` — GroupCreateRequest, GroupUpdateRequest, GroupResponse, GroupPublicResponse, PickupSlotRequest/Response

### 프론트엔드

#### 6. 공구 생성 화면
- `apps/web/src/routes/(owner)/groups/create/+page.svelte`:
  - 필수 입력: 상품명, 가격, 마감 시간 (빠른 선택: 오늘 오후6시/자정/직접), 사진
  - 고급 옵션 (접어둠, 기본 예약주문형): 타입, 최소 수량(공동구매형), 픽업 시간대(픽업형), 판매 가능 수량, 상품 설명
  - 이미지 업로드: presign → R2 직접 업로드 → image_url 저장
  - 게시 → 완료 화면 (공유 링크 복사 + 카카오 공유 버튼)

#### 7. 공구 상세 — 공개 (SSR)
- `apps/web/src/routes/g/[publicId]/+page.server.ts` — SSR load: public API 호출
- `apps/web/src/routes/g/[publicId]/+page.svelte`:
  - 상품명, 가격, 사진, 마감 카운트다운
  - 공동구매형: 진행 현황 바 (현재/최소)
  - 한정 수량: 잔여 n개
  - 품절/마감 시 CTA 비활성
  - 마감/완료 공구: 상태 안내 + "이 매장의 진행 중 공구 보기"
  - OG meta 태그 (상품명, 가격, 이미지)
  - CTA: "주문하기" (Phase 5에서 결제 연결)

#### 8. 공구 수정
- `apps/web/src/routes/(owner)/groups/[groupId]/edit/+page.svelte` — 수정 폼

#### 9. 사장님 공구 상세
- `apps/web/src/routes/(owner)/groups/[groupId]/+page.svelte` — 주문 현황, 공유 링크, 조기 마감 버튼

### 테스트
- `apps/api/tests/test_groups.py`:
  - 공구 생성 → public_id 반환 확인
  - 공개 조회 (public_id)
  - 수정 제한 (마감 후 수정 시도 → 에러)
  - 삭제 조건 (주문 있으면 삭제 불가)
  - presign URL 발급 확인

## 검증
```bash
# 백엔드 테스트
cd apps/api && pytest tests/test_groups.py -v

# 프론트 빌드
cd apps/web && npm run build

# 통합 (수동)
# 사장님 로그인 → 공구 생성 → 공유 링크 → 비로그인 브라우저에서 공개 조회
```
