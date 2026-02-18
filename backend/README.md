# Backend

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL (PostGIS)
- uv package manager

## Setup

```powershell
copy .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Commands

- `uv run uvicorn app.main:app --reload --port 8000`
- `uv run ruff check .`
- `uv run ruff format --check .`

## Health Endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

