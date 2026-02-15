# Simplify Deployment - Clone & Run Design

**Date:** 2026-02-15  
**Status:** Approved  
**Goal:** Simplify deployment so users can run with minimal configuration after git clone

---

## Problem Statement

Currently, deploying the exchange-gateway requires:
1. Running `./scripts/setup-secrets.sh --dev` (requires Bash, not Windows-friendly)
2. Using different docker-compose files for dev/prod
3. Managing secrets in separate files outside of `.env`

**Target:** Users should be able to deploy with just:
```bash
git clone <repo>
cp .env.example .env
# Edit .env for Exchange config
docker compose up -d
```

---

## Proposed Solution

### 1. Single docker-compose.yml

- **Remove:** `docker-compose.dev.yml`
- **Keep:** Single `docker-compose.yml` with development-friendly defaults
- **Development mode:** Controlled via `DEBUG=true` in `.env`

### 2. Remove setup-secrets.sh

- **Remove:** `scripts/setup-secrets.sh`
- **All secrets managed in `.env`** - simpler, Windows-friendly

### 3. Complete .env.example

Expand `.env.example` to include ALL required configuration:

| Variable | Description | Default (dev) |
|----------|-------------|---------------|
| DB_HOST | Database host | mysql |
| DB_PORT | Database port | 3306 |
| DB_USER | Database user | root |
| DB_PASSWORD | Database password | root123 |
| DB_NAME | Database name | vue_fastapi_admin |
| SECRET_KEY | JWT secret key | (generate random) |
| EXCHANGE_ENCRYPTION_KEY | Password encryption key | (generate random) |
| EXCHANGE_SERVER | Exchange server address | 10.72.8.110 |
| EXCHANGE_DOMAIN | Exchange domain | hnanet |
| EXCHANGE_EMAIL_SUFFIX | Email suffix | @tianjin-air.com |
| DEBUG | Debug mode | true |
| NGINX_PORT | HTTP port | 80 |
| WORKERS | Worker processes | 2 |

### 4. Update docker-compose.yml

- Replace secrets file references with environment variables
- Remove production-only features (SSL, healthchecks for stability)
- Use ports for easy access during development

---

## User Workflow

### Development
```bash
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway
cp .env.example .env
# Edit .env - at minimum configure Exchange server
docker compose up -d
```

### Production
```bash
# Same workflow, but edit .env with production values
# Consider securing SECRET_KEY and EXCHANGE_ENCRYPTION_KEY with proper values
```

---

## Files to Modify

| File | Action |
|------|--------|
| `.env.example` | Expand with all config options |
| `docker-compose.yml` | Merge dev config, remove secrets |
| `docker-compose.dev.yml` | Delete |
| `scripts/setup-secrets.sh` | Delete |

---

## Rollback Plan

If users need production-grade secrets management, they can:
1. Mount secrets as files
2. Use Docker secrets externally
3. Reference original implementation in git history

---

## Testing

Verify the deployment works:
```bash
docker compose up -d
# Check all services running
docker compose ps
# Test access
curl http://localhost/api/v1/exchange/health
```
