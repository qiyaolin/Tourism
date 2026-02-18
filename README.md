# Project Atlas

Phase 1.1 infrastructure baseline for:

- `frontend`: Vue 3 + Vite + TypeScript
- `backend`: FastAPI + uv + SQLAlchemy
- `infra`: PostgreSQL + PostGIS via Docker Compose

## Quick Start

1. Start database:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

2. Backend:

```powershell
cd backend
copy .env.example .env
uv sync
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

## Notes

- Cloudflare Tunnel and HTTPS are documented in `infra/cloudflare/README.md`.
- Storage abstraction plan is documented in `infra/storage/README.md`.

