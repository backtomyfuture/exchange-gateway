# Simplify Deployment - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify deployment so users can run with minimal configuration after git clone

**Architecture:** Single docker-compose.yml with all config in .env, removing shell scripts for secrets management

**Tech Stack:** Docker Compose, Environment Variables

---

## Task 1: Update .env.example with Complete Configuration

**Files:**
- Modify: `.env.example`

**Step 1: Replace .env.example content**

```bash
# =============================================================================
# Exchange Gateway - Environment Configuration
# 
# Usage: cp .env.example .env
# Then edit .env with your values
# =============================================================================

# ===========================================
# Database Configuration
# ===========================================
DB_HOST=mysql
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root123
DB_NAME=vue_fastapi_admin

# ===========================================
# Security Configuration
# ===========================================
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=dev-secret-key-change-in-production
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
EXCHANGE_ENCRYPTION_KEY=dev-encryption-key-change-in-production

# ===========================================
# Exchange Mail Service Configuration
# ===========================================
EXCHANGE_SERVER=10.72.8.110
EXCHANGE_DOMAIN=hnanet
EXCHANGE_EMAIL_SUFFIX=@tianjin-air.com

# ===========================================
# Application Settings
# ===========================================
DEBUG=true
WORKERS=2

# ===========================================
# Nginx Configuration
# ===========================================
NGINX_PORT=80
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "feat: expand .env.example with complete configuration"
```

---

## Task 2: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Replace docker-compose.yml content**

```yaml
# Exchange Gateway - Docker Compose Configuration
# 
# Usage: 
#   cp .env.example .env
#   # Edit .env with your Exchange server configuration
#   docker compose up -d
#
# For development: Set DEBUG=true in .env

services:
  # ===========================================
  # MySQL Database
  # ===========================================
  mysql:
    image: mysql:8.0
    container_name: exchange-gateway-mysql
    restart: unless-stopped
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-authentication-plugin=mysql_native_password
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-root123}
      MYSQL_DATABASE: ${DB_NAME:-vue_fastapi_admin}
      MYSQL_USER: ${DB_USER:-root}
      MYSQL_PASSWORD: ${DB_PASSWORD:-root123}
    ports:
      - "13306:3306"
    volumes:
      - ./.docker-data/mysql:/var/lib/mysql
    networks:
      - backend

  # ===========================================
  # FastAPI Application
  # ===========================================
  app:
    build:
      context: .
      dockerfile: deploy/app/Dockerfile
    image: exchange-app:latest
    container_name: exchange-gateway-app
    restart: unless-stopped
    environment:
      - DEBUG=${DEBUG:-true}
      - DEV_MODE=${DEBUG:-true}
      - DB_HOST=${DB_HOST:-mysql}
      - DB_PORT=${DB_PORT:-3306}
      - DB_USER=${DB_USER:-root}
      - DB_PASSWORD=${DB_PASSWORD:-root123}
      - DB_NAME=${DB_NAME:-vue_fastapi_admin}
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}
      - WORKERS=${WORKERS:-2}
      # Exchange mail service configuration
      - EXCHANGE_SERVER=${EXCHANGE_SERVER:-10.72.8.110}
      - EXCHANGE_DOMAIN=${EXCHANGE_DOMAIN:-hnanet}
      - EXCHANGE_EMAIL_SUFFIX=${EXCHANGE_EMAIL_SUFFIX:-@tianjin-air.com}
      - EXCHANGE_ENCRYPTION_KEY=${EXCHANGE_ENCRYPTION_KEY:-dev-encryption-key-change-in-production}
      - WEBHOOK_ALLOW_PRIVATE_URLS=true
    ports:
      - "18001:8000"
    depends_on:
      - mysql
    volumes:
      - ./app:/opt/app/app:ro
      - ./.docker-data/logs:/var/log/app
      - ./pyproject.toml:/opt/app/pyproject.toml:ro
      - ./migrations:/opt/app/migrations:ro
      - ./tests:/opt/app/tests:ro
      - ./pytest.ini:/opt/app/pytest.ini:ro
    networks:
      - backend
      - frontend

  # ===========================================
  # Webhook Listener Worker
  # ===========================================
  webhook-worker:
    image: exchange-app:latest
    container_name: exchange-gateway-webhook-worker
    restart: unless-stopped
    entrypoint: ["python3", "-m", "app.services.exchange.webhook_listener"]
    environment:
      - DEBUG=${DEBUG:-true}
      - DB_HOST=${DB_HOST:-mysql}
      - DB_PORT=${DB_PORT:-3306}
      - DB_USER=${DB_USER:-root}
      - DB_PASSWORD=${DB_PASSWORD:-root123}
      - DB_NAME=${DB_NAME:-vue_fastapi_admin}
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}
      - EXCHANGE_ENCRYPTION_KEY=${EXCHANGE_ENCRYPTION_KEY:-dev-encryption-key-change-in-production}
      - WEBHOOK_ALLOW_PRIVATE_URLS=true
    depends_on:
      - mysql
      - app
    volumes:
      - ./app:/opt/app/app:ro
      - ./migrations:/opt/app/migrations
      - ./.docker-data/logs:/var/log/app
    networks:
      - backend

  # ===========================================
  # Nginx Reverse Proxy
  # ===========================================
  nginx:
    build:
      context: .
      dockerfile: deploy/nginx/Dockerfile
    container_name: exchange-gateway-nginx
    restart: unless-stopped
    ports:
      - "${NGINX_PORT:-80}:80"
    depends_on:
      - app
    networks:
      - frontend

# ===========================================
# Networks
# ===========================================
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: simplify docker-compose with env-based config"
```

---

## Task 3: Delete docker-compose.dev.yml

**Files:**
- Delete: `docker-compose.dev.yml`

**Step 1: Delete file**

```bash
rm docker-compose.dev.yml
```

**Step 2: Commit**

```bash
git rm docker-compose.dev.yml
git commit -m "refactor: remove docker-compose.dev.yml, use single docker-compose.yml"
```

---

## Task 4: Delete setup-secrets.sh

**Files:**
- Delete: `scripts/setup-secrets.sh`

**Step 1: Delete file**

```bash
rm scripts/setup-secrets.sh
```

**Step 2: Commit**

```bash
git rm scripts/setup-secrets.sh
git commit -m "refactor: remove setup-secrets.sh, use .env for config"
```

---

## Task 5: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Update Quick Start section**

Replace the Development section with:

```markdown
### Quick Start

```bash
# Clone the repository
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway

# Copy and edit environment configuration
cp .env.example .env
# Edit .env to configure your Exchange server

# Start services
docker compose up -d
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: simplify quick start instructions"
```

---

## Task 6: Verify Deployment

**Step 1: Start services**

```bash
docker compose down -v  # Clean up if needed
docker compose up -d
```

**Step 2: Check services**

```bash
docker compose ps
```

**Step 3: Test health endpoint**

```bash
curl http://localhost:18001/api/v1/exchange/health
```

**Expected: JSON response with health status**

**Step 4: Commit**

```bash
git add .
git commit -m "test: verify simplified deployment works"
```
