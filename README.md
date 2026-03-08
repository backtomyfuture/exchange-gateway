# Exchange Gateway

[![CI](https://github.com/f148002/exchange-gateway/actions/workflows/test.yml/badge.svg)](https://github.com/f148002/exchange-gateway/actions)
[![License](https://img.shields.io/github/license/f148002/exchange-gateway)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)

REST API gateway for Microsoft Exchange / EWS with an admin dashboard.

| Category | Details |
|----------|---------|
| **Email API** | Send, receive, search, reply, forward — all via `X-Api-Key` |
| **Templates** | Jinja2 variable substitution, preview before send |
| **Webhooks** | Real-time Exchange streaming events (NewMail, Created, …) |
| **Dashboard** | Vue 3 + Naive UI — manage accounts, keys, templates, logs |
| **i18n** | Chinese / English, switchable at runtime |
| **Security** | AES-256-GCM encryption, SHA-256 key hashing, Docker Secrets |
| **Observability** | Structured logging (structlog), Prometheus `/metrics`, audit trail |

## Quick Start

```bash
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway

# 1. Generate secrets & copy env
make init                         # or: ./scripts/init-secrets.sh && cp .env.example .env

# 2. (Optional) Edit .env — set EXCHANGE_SERVER, EXCHANGE_DOMAIN, etc.

# 3. Start everything
docker compose up -d              # or: make dev
```

| Endpoint | URL |
|----------|-----|
| Dashboard | http://localhost |
| API Docs (Swagger) | http://localhost:18001/docs |
| Health Check | http://localhost:18001/health |

Default login: **admin / 123456**

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

| Service | Role |
|---------|------|
| `app` | FastAPI backend — API, auth, migrations |
| `nginx` | Reverse proxy + serves Vue 3 SPA |
| `arq-worker` | Async task queue (email send, webhook delivery) |
| `webhook-worker` | Exchange streaming event listener |
| `mysql` | Primary database |
| `redis` | Task queue + rate limiting |

### Using an External Database or Redis

The bundled MySQL and Redis run by default. To use your own:

1. Comment out `mysql` (or `redis`) in `docker-compose.yml`.
2. Update `.env`:
   ```env
   DB_HOST=your-mysql-host
   DB_PORT=3306
   # For Redis:
   REDIS_URL=redis://your-redis-host:6379/0
   ```
3. Put the database password in `secrets/db_password`.

## API Usage

```bash
# Send email
curl -X POST http://localhost:18001/api/v1/exchange/emails/send \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"account_id":1,"to":["user@example.com"],"subject":"Hello","body":"Hi"}'

# Subscribe to events
curl -X POST http://localhost:18001/api/v1/exchange/webhooks/create \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://yourserver.com/hook","events":["NewMailEvent"],"secret":"s3cret"}'
```

Full API reference at `/docs` (Swagger UI).

## Development

```bash
make install          # install Python + frontend deps
make lint             # ruff + eslint
make test             # pytest (189 tests)
make build            # build Docker images
make web-dev          # Vite dev server on :3000
```

Run `make help` to see all available commands.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Tortoise ORM, exchangelib, ARQ |
| Frontend | Vue 3, Vite, Naive UI, Pinia, vue-i18n |
| Database | MySQL 8.0, Redis 7 |
| Infra | Docker Compose, Nginx, Prometheus |

## License

[Apache License 2.0](LICENSE) — based on [vue-fastapi-admin](https://github.com/mizhexiaoxiao/vue-fastapi-admin) (MIT).
