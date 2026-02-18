# Project Atlas

Phase 1.1 infrastructure baseline for:

- `frontend`: Vue 3 + Vite + TypeScript
- `backend`: FastAPI + uv + SQLAlchemy
- `infra`: PostgreSQL + PostGIS via Docker Compose

## Quick Start

### Option A: Docker (Recommended)

Run full stack in isolated containers:

```powershell
docker compose -f infra/docker-compose.yml up --build
```

Access:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`
- Health live: `http://localhost:8000/api/v1/health/live`

### Option B: Local Runtime

1. Start database:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

2. Backend:

```powershell
cd backend
copy .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

3. Frontend:

```powershell
cd frontend
copy .env.example .env
pnpm install
pnpm dev
```

4. Validate:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`
- Health live: `http://localhost:8000/api/v1/health/live`
- Health ready: `http://localhost:8000/api/v1/health/ready`

## API Contract

OpenAPI from FastAPI is the single source of truth:

- `/docs`
- `/openapi.json`

## Phase 1.2 Auth Flow

1. Send verification code: `POST /api/v1/auth/send-code`
2. Login or auto-register: `POST /api/v1/auth/login`
3. Get current user: `GET /api/v1/auth/me` with bearer token

## Phase 1.3 Data APIs

- POI CRUD: `/api/v1/pois`
- Itinerary CRUD: `/api/v1/itineraries`
- Itinerary item APIs: `/api/v1/itineraries/{id}/items`

## Notes

- Cloudflare Tunnel and HTTPS are documented in `infra/cloudflare/README.md`.
- Storage abstraction plan is documented in `infra/storage/README.md`.
- Docker mode avoids local conda/venv PATH conflicts during development.

## Session Recovery

For multi-session development continuity:

1. Read `PROGRESS.md` first.
2. Summarize `current phase`, `current task`, `blockers`, and `next action`.
3. Update `PROGRESS.md` after each verifiable sub-task.
