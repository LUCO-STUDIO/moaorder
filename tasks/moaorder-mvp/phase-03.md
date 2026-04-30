# Phase 3: 인증 + 온보딩 + 공통 UI

## 목표
카카오 로그인 → JWT 발급 → 역할 분기 → 온보딩까지 동작. 프론트 공통 UI 기반 완성.

## 컨텍스트
- 설계 문서: `docs/code-architecture.md` (인증 흐름, 권한 dependency)
- 설계 문서: `docs/flow.md` (고객/사장님 온보딩, 네비게이션, 탭 구조)
- 설계 문서: `docs/adr.md` (ADR-010 단일 JWT, ADR-017 자동 구독)
- Phase 2의 SQLAlchemy 모델 사용

## 구현 항목

### 백엔드

#### 1. 카카오 OAuth
- `apps/api/app/api/auth.py`:
  - `POST /api/auth/kakao/exchange` — body: {code}. 카카오 토큰 교환 → 사용자 조회/생성 → JWT 발급 → httpOnly 쿠키 설정
  - `POST /api/auth/logout` — 쿠키 삭제
  - `GET /api/auth/me` — 현재 사용자 정보 반환
- `apps/api/app/core/auth.py`:
  - JWT 생성: `create_access_token(user_id, role)` — 7일 만료
  - JWT 검증: `verify_token(token)` → user_id, role
  - dependency: `get_current_user`, `require_auth`, `require_owner`
  - store ownership 검증: path param의 store_id를 받아 현재 사용자가 해당 매장의 owner인지 서비스 레이어에서 체크 (별도 dependency 또는 서비스 함수)
  - 카카오 API 호출: `exchange_kakao_code(code)` → kakao_id, nickname, profile_image

#### 2. 온보딩 API
- `apps/api/app/api/onboarding.py`:
  - `POST /api/onboarding/owner` — 매장명, 운영자명, 연락처, 지역, 카테고리 → Store 생성 + store_members 생성
  - `POST /api/onboarding/customer` — 닉네임, 지역, 카테고리 → User 업데이트

#### 3. 사용자/매장/구독 API
- `apps/api/app/api/users.py`:
  - `PATCH /api/users/me` — 닉네임, 지역, 카테고리 수정
- `apps/api/app/api/stores.py`:
  - `GET /api/stores/{store_id}` — 매장 정보 (공개)
  - `PATCH /api/stores/{store_id}` — 매장 정보 수정 (사장님만)
- `apps/api/app/api/subscriptions.py`:
  - `POST /api/subscriptions` — body: {store_id}. 구독 생성 (중복 방지)
  - `DELETE /api/subscriptions/stores/{store_id}` — 구독 해제 (soft delete)
  - `GET /api/subscriptions/my` — 내 구독 매장 목록

#### 4. Pydantic 스키마
- `apps/api/app/schemas/auth.py` — KakaoExchangeRequest, TokenResponse, UserResponse
- `apps/api/app/schemas/onboarding.py` — OwnerOnboardingRequest, CustomerOnboardingRequest
- `apps/api/app/schemas/user.py` — UserUpdateRequest
- `apps/api/app/schemas/store.py` — StoreResponse, StoreUpdateRequest
- `apps/api/app/schemas/subscription.py` — SubscriptionRequest, SubscriptionResponse

### 프론트엔드

#### 5. 공통 UI Primitives
`apps/web/src/lib/components/ui/`:
- `Button.svelte` — primary, secondary, danger, disabled, loading 상태
- `Input.svelte` — label, placeholder, error 메시지
- `Card.svelte` — 기본 카드 컨테이너
- `Badge.svelte` — 상태 배지 (색상 variant)
- `Tabs.svelte` + `TabItem.svelte` — 탭 전환
- `BottomNav.svelte` — 하단 탭 네비게이션

#### 6. 레이아웃
- `apps/web/src/routes/(customer)/+layout.svelte` — 고객 레이아웃 (하단 4탭: 홈/주문내역/알림/마이)
- `apps/web/src/routes/(owner)/+layout.svelte` — 사장님 레이아웃 (하단 4탭: 대시보드/공구관리/알림/마이 + FAB)
- auth guard: 미로그인 시 로그인 페이지로 리다이렉트
- role guard: 역할에 맞지 않는 경로 접근 시 리다이렉트

#### 7. 인증 화면
- `apps/web/src/routes/auth/login/+page.svelte` — 카카오 로그인 버튼 (카카오 인가 URL로 리다이렉트)
- `apps/web/src/routes/auth/kakao/callback/+page.svelte` — 콜백 처리 (code → API exchange → 역할 분기)
- `apps/web/src/lib/stores/auth.ts` — 인증 상태 스토어 (user, isLoggedIn, role)

#### 8. 온보딩 화면
- `apps/web/src/routes/onboarding/owner/+page.svelte` — 매장 정보 입력 폼
- `apps/web/src/routes/onboarding/customer/+page.svelte` — 닉네임, 지역, 카테고리 입력

#### 9. 마이페이지 + 구독 관리
- `apps/web/src/routes/(customer)/my/+page.svelte` — 고객 마이페이지
- `apps/web/src/routes/(customer)/my/subscriptions/+page.svelte` — 매장 구독 관리
- `apps/web/src/routes/(owner)/my/+page.svelte` — 사장님 마이페이지 (매장 정보 수정)

### 테스트
- `apps/api/tests/test_auth.py`:
  - 카카오 OAuth mock → JWT 발급 확인
  - JWT 쿠키 → /api/auth/me 정상 응답
  - 만료 JWT → 401
  - require_owner dependency → 고객은 403

## 검증
```bash
# 백엔드
cd apps/api && pytest tests/test_auth.py -v

# 프론트엔드
cd apps/web && npm run build  # 빌드 에러 없음

# 통합 (수동)
# 1. http://localhost:5173 접속
# 2. 카카오 로그인 버튼 → 카카오 인가 → 콜백 → 역할 분기
# 3. 온보딩 → 홈 리다이렉트
```
