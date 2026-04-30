# 모아오더 (MoaOrder)

공동구매 SaaS 플랫폼 — 동네 가게 사장님과 고객을 위한 공동구매·예약주문·픽업 서비스.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | SvelteKit + TypeScript + Tailwind CSS v4 |
| Backend | FastAPI (async) + SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 |
| 인증 | 카카오 OAuth → JWT |
| 결제 | PortOne v2 |
| 이미지 | Cloudflare R2 (Presigned URL) |
| 배포 | Vercel (프론트) + Railway (백엔드/DB) |

## 모노레포 구조

```
moaorder/
├── apps/
│   ├── web/          # SvelteKit 프론트엔드
│   └── api/          # FastAPI 백엔드 + Worker
├── docs/             # 설계 문서
└── docker-compose.yml
```

## 로컬 개발 환경

### 사전 요구사항

- Node.js 20+
- pnpm 10+ (`npm i -g pnpm`)
- Python 3.12+
- Docker & Docker Compose

### 실행

```bash
# 1. PostgreSQL
docker compose up -d

# 2. FastAPI
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 3. SvelteKit (루트에서 실행)
pnpm install          # 모노레포 전체 설치
cp apps/web/.env.example apps/web/.env
pnpm dev              # = pnpm --filter web dev
```

### 접속

- 프론트엔드: http://localhost:5173
- API 헬스체크: http://localhost:8000/api/health
- PostgreSQL: localhost:5433 (다른 프로젝트와 충돌 방지)
