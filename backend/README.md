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
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Docker

Backend is normally started by root compose:

```powershell
docker compose -f infra/docker-compose.yml up --build backend
```

## Commands

- `uv run uvicorn app.main:app --reload --port 8000`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run alembic upgrade head`

## Health Endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

## Auth Endpoints

- `POST /api/v1/auth/send-code`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

## Phase 1.3 P0 Endpoints

- `POST /api/v1/pois`
- `GET /api/v1/pois`
- `GET /api/v1/pois/{id}`
- `PUT /api/v1/pois/{id}`
- `DELETE /api/v1/pois/{id}`
- `POST /api/v1/itineraries`
- `GET /api/v1/itineraries`
- `GET /api/v1/itineraries/{id}`
- `PUT /api/v1/itineraries/{id}`
- `DELETE /api/v1/itineraries/{id}`
- `POST /api/v1/itineraries/{id}/items`
- `PUT /api/v1/itineraries/{id}/items/{item_id}`
- `DELETE /api/v1/itineraries/{id}/items/{item_id}`
