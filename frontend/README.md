# Frontend

## Stack

- Vue 3
- Vite
- TypeScript
- ESLint + Prettier

## Setup

```powershell
copy .env.example .env
pnpm install
pnpm dev
```

## Docker

Frontend is normally started by root compose:

```powershell
docker compose -f infra/docker-compose.yml up --build frontend
```

## Commands

- `pnpm dev`
- `pnpm build`
- `pnpm lint`
- `pnpm format`
- `pnpm format:check`

## Environment

- `VITE_API_BASE_URL`: backend API base URL, default `http://localhost:8000/api/v1`
