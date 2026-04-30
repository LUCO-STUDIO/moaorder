# Phase 1: 모노레포 부트스트랩

## 목표
프로젝트 기본 구조가 잡히고, SvelteKit / FastAPI / PostgreSQL이 각각 빈 상태로 실행되는 것.

## 컨텍스트
- 설계 문서: `docs/code-architecture.md` (모노레포 구조, 기술 스택)
- 설계 문서: `docs/adr.md` (ADR-001 SvelteKit, ADR-002 FastAPI, ADR-016 배포 구조)

## 구현 항목

### 1. 루트 프로젝트 설정
- 루트에 `.gitignore` 생성 (node_modules, __pycache__, .env, .venv, alembic/versions/*.pyc 등)
- 루트에 `README.md` 생성 (프로젝트 개요, 로컬 실행 방법)

### 2. `apps/web` — SvelteKit
- `apps/web/` 디렉토리에 SvelteKit 프로젝트 생성 (`npm create svelte@latest`)
  - TypeScript 사용
  - adapter-auto 또는 adapter-vercel
- Tailwind CSS v4 설치 및 설정
- `apps/web/src/lib/api.ts` — API 클라이언트 유틸 (fetch wrapper, 에러 처리, base URL 설정)
- `apps/web/src/routes/+layout.svelte` — 빈 기본 레이아웃
- `apps/web/src/routes/+page.svelte` — "모아오더" 텍스트만 표시하는 홈
- `apps/web/.env.example`:
  ```
  PUBLIC_API_URL=http://localhost:8000/api
  ```

### 3. `apps/api` — FastAPI
- `apps/api/` 디렉토리에 Python 프로젝트 구조:
  ```
  apps/api/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py          # FastAPI app, CORS, 미들웨어
  │   ├── api/
  │   │   ├── __init__.py
  │   │   └── health.py    # GET /api/health
  │   ├── core/
  │   │   ├── __init__.py
  │   │   ├── config.py    # Settings (pydantic-settings, .env 로드)
  │   │   ├── database.py  # async engine, session dependency
  │   │   └── middleware.py # request_id 미들웨어
  │   ├── models/
  │   │   └── __init__.py
  │   ├── schemas/
  │   │   ├── __init__.py
  │   │   └── common.py    # ErrorResponse, request_id
  │   ├── services/
  │   │   └── __init__.py
  │   └── workers/
  │       └── __init__.py
  ├── requirements.txt
  └── .env.example
  ```
- `app/main.py`:
  - FastAPI 앱 생성
  - CORS 설정 (`http://localhost:5173`, credentials=True)
  - request_id 미들웨어 등록
  - 에러 핸들러 (통일된 JSON 형식 + request_id)
  - `/api/health` 라우터 등록
- `app/core/config.py`:
  - pydantic-settings 기반 Settings 클래스
  - DATABASE_URL, KAKAO_CLIENT_ID, PORTONE_API_SECRET 등 전체 환경변수 정의
- `app/core/middleware.py`:
  - request_id 미들웨어: `X-Request-ID` 헤더 있으면 재사용, 없으면 UUID 생성
  - 응답 헤더에 `X-Request-ID` 포함
- `app/core/database.py`:
  - async SQLAlchemy engine + async session factory
  - `get_db` dependency
- `app/schemas/common.py`:
  - `ErrorDetail(code, message, detail, request_id)`
  - `ErrorResponse(error: ErrorDetail)`
- `requirements.txt`:
  ```
  fastapi>=0.115.0
  uvicorn[standard]>=0.30.0
  sqlalchemy[asyncio]>=2.0.0
  asyncpg>=0.30.0
  alembic>=1.14.0
  pydantic>=2.0.0
  pydantic-settings>=2.0.0
  python-jose[cryptography]>=3.3.0
  httpx>=0.27.0
  nanoid>=2.0.0
  boto3>=1.35.0
  resend>=2.0.0
  ```
- `.env.example`:
  ```
  DATABASE_URL=postgresql+asyncpg://moaorder:moaorder@localhost:5432/moaorder
  JWT_SECRET=change-me-in-production
  JWT_EXPIRE_DAYS=7
  KAKAO_CLIENT_ID=
  KAKAO_CLIENT_SECRET=
  KAKAO_REDIRECT_URI=http://localhost:5173/auth/kakao/callback
  PORTONE_STORE_ID=
  PORTONE_API_SECRET=
  PORTONE_CHANNEL_KEY=
  R2_ACCOUNT_ID=
  R2_ACCESS_KEY_ID=
  R2_SECRET_ACCESS_KEY=
  R2_BUCKET=
  R2_PUBLIC_BASE_URL=
  RESEND_API_KEY=
  EMAIL_FROM=
  EMAIL_REPLY_TO=
  ```

### 4. Docker Compose
- `docker-compose.yml`:
  ```yaml
  services:
    postgres:
      image: postgres:16
      environment:
        POSTGRES_USER: moaorder
        POSTGRES_PASSWORD: moaorder
        POSTGRES_DB: moaorder
      ports:
        - "5432:5432"
      volumes:
        - pgdata:/var/lib/postgresql/data
  volumes:
    pgdata:
  ```

## 검증
```bash
# 1. PostgreSQL 실행
docker compose up -d
# → postgres 컨테이너 running

# 2. FastAPI 실행
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/api/health 응답: {"status": "ok"}

# 3. SvelteKit 실행
cd apps/web && npm install && npm run dev
# → http://localhost:5173 페이지 표시

# 4. CORS 확인
curl -H "Origin: http://localhost:5173" -I http://localhost:8000/api/health
# → Access-Control-Allow-Origin 헤더 포함

# 5. Worker import 확인
cd apps/api && python -c "from app.workers import main; print('Worker module OK')"
```
