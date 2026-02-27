# Exchange Gateway

[![CI](https://github.com/f148002/exchange-gateway/actions/workflows/test.yml/badge.svg)](https://github.com/f148002/exchange-gateway/actions)
[![License](https://img.shields.io/github/license/f148002/exchange-gateway)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)

REST API gateway for Microsoft Exchange / EWS with an admin dashboard.

## Features

| Category | Details |
|----------|---------|
| **Email API** | Send, receive, search, reply, forward — all via `X-Api-Key` |
| **Templates** | Jinja2 variable substitution, preview before send |
| **Webhooks** | Real-time Exchange streaming events (NewMail, Created, …) |
| **Dashboard** | Vue 3 + Naive UI — manage accounts, keys, templates, logs |
| **Security** | AES-256-GCM encryption, SHA-256 key hashing, Docker Secrets |
| **Observability** | Structured logging (structlog), Prometheus `/metrics`, audit trail |

## Quick Start

```bash
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway

# Generate secrets & configure
./scripts/init-secrets.sh
cp .env.example .env          # edit DATABASE_URL, EXCHANGE_SERVER, etc.

# Launch (includes MySQL + Redis)
docker compose --profile local-db --profile local-redis up -d
```

| Endpoint | URL |
|----------|-----|
| Dashboard | http://localhost |
| API Docs (Swagger) | http://localhost/docs |
| Health Check | http://localhost:18001/health |

Default login: `admin` / `123456`

## Architecture

```
┌─────────┐      ┌──────────────┐      ┌───────┐
│  Nginx  │─────▶│  FastAPI App │─────▶│ MySQL │
│ (+ Vue) │      │   (Gunicorn) │      └───────┘
└─────────┘      └──────┬───────┘
                        │            ┌───────┐
                        ├───────────▶│ Redis │
                        │            └───┬───┘
                 ┌──────┴───────┐       │
                 │  ARQ Worker  │◀──────┘
                 │ Webhook Wkr  │
                 └──────────────┘
```

**Services** (all via Docker Compose):

| Service | Role |
|---------|------|
| `app` | FastAPI backend — API + auth + migrations |
| `nginx` | Reverse proxy + serves Vue 3 SPA |
| `arq-worker` | Async task queue (email send, webhook delivery) |
| `webhook-worker` | Exchange streaming event listener |
| `mysql` | Primary database (profile: `local-db`) |
| `redis` | Task queue + rate limiting (profile: `local-redis`) |

## API Usage

```bash
# Send email
curl -X POST http://localhost:18001/api/v1/exchange/emails/send \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"account_id":1,"to":["user@example.com"],"subject":"Hello","body":"<p>Hi</p>","body_type":"html"}'

# Subscribe to events
curl -X POST http://localhost:18001/api/v1/exchange/webhooks/create \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://yourserver.com/hook","events":["NewMailEvent"],"secret":"s3cret"}'
```

Full API reference available at `/docs` (Swagger UI).

## Development

```bash
pip install -r requirements.txt   # backend deps
cd web && pnpm install             # frontend deps

# Lint & format
ruff check app/ tests/ scripts/
ruff format app/ tests/ scripts/

# Test (189 tests)
pytest tests/ -v --ignore=tests/integration/ --ignore=tests/manual/
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Tortoise ORM, exchangelib, ARQ |
| Frontend | Vue 3, Vite, Naive UI, Pinia |
| Database | MySQL 8.0, Redis 7 |
| Infra | Docker, Nginx, Prometheus |

## License

[Apache License 2.0](LICENSE) — based on [vue-fastapi-admin](https://github.com/mizhexiaoxiao/vue-fastapi-admin) (MIT).
