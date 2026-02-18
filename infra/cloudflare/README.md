# Cloudflare Tunnel Plan (Phase 1.1 Reserved)

Phase 1.1 does not bind a production domain yet. This folder keeps reusable setup docs.

## Goal

Expose local HTTP services through Cloudflare and provide external HTTPS access later.

## Prerequisites

- Cloudflare account
- Managed domain in Cloudflare
- Tunnel token
- `cloudflared` installed locally

## Example Workflow

```powershell
cloudflared tunnel login
cloudflared tunnel create atlas-dev
cloudflared tunnel route dns atlas-dev api.example.com
```

Run tunnel with config:

```powershell
cloudflared tunnel --config infra/cloudflare/config.example.yml run
```

## HTTPS Path

Local HTTP service -> Cloudflare Tunnel -> Public HTTPS endpoint

## Security Notes

- Never commit real tunnel token.
- Keep production and dev tunnels isolated.

