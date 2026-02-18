# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**exchange-gateway** is an enterprise-grade Exchange/EWS mail gateway providing:
- RESTful API for email operations (send, receive, search) with API Key authentication
- Email templates with variable substitution
- Webhook support for Exchange events (NewMail, Created, Modified, etc.)
- Admin dashboard for account and API key management
- AES-256-GCM password encryption, API Key hashing, and key rotation capabilities

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, Tortoise ORM, exchangelib, arq |
| Frontend | Vue 3, Vite, Naive UI, Pinia |
| Database | MySQL 8.0, Redis (for Task Queue & Rate Limiting) |
| Deployment | Docker, Nginx, Prometheus (Monitoring) |

## Development Commands

### Backend Setup

```bash
# Install dependencies (requires Python 3.11+)
pip install -r requirements.txt

# Run with Docker Compose (all services)
docker compose up -d

# Run backend only (after starting MySQL)
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Linting & Formatting

```bash
# Check code style with Ruff
ruff check app/ tests/ scripts/

# Auto-fix issues
ruff check --fix app/ tests/ scripts/

# Format code
ruff format app/ tests/ scripts/
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/path/to/test_file.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Run only unit tests (skip integration tests)
pytest tests/ -v --ignore=tests/integration/
```

### Database Migrations

```bash
# Create new migration
aerich migrate --name migration_name

# Apply migrations
aerich upgrade

# Downgrade last migration
aerich downgrade
```

### Frontend Development

```bash
cd web

# Development server
pnpm dev

# Production build
pnpm build

# Linting
pnpm lint
pnpm lint:fix

# Formatting
pnpm prettier
```

### Key Rotation

```bash
# Test key rotation (dry-run)
python scripts/rotate_key.py --old-key "old-key" --new-key "new-key" --dry-run

# Execute key rotation
python scripts/rotate_key.py --old-key "old-key" --new-key "new-key"
```

## Architecture & Code Structure

### High-Level Architecture

```
FastAPI Application
├── API Layer (app/api/v1/)
│   ├── Exchange APIs (emails, accounts, contacts, templates, webhooks)
│   ├── Admin APIs (users, roles, menus, API keys, audit logs)
│   └── Base authentication
├── Service Layer (app/services/exchange/)
│   ├── EmailService: Send/receive/search emails
│   ├── AccountService: Manage Exchange accounts
│   ├── WebhookService: Subscribe to Exchange events
│   ├── ContactService: Manage contacts
│   └── ExchangeConnectionPool: Connection pooling for Exchange
├── Data Layer (app/models/)
│   ├── Exchange models (Account, Email, Template, Webhook)
│   ├── Admin models (User, Role, Menu, API)
│   └── Audit models
└── Core (app/core/)
    ├── Exception handlers
    ├── Authentication & authorization
    ├── Middlewares (audit logging, request tracking)
    └── Rate limiting
```

### Key Concepts

1. **API Key Authentication**: Exchange Gateway API uses X-Api-Key header authentication. Keys are SHA-256 hashed in database.
   - Location: `app/core/api_key_auth.py`

2. **Password Encryption**: Exchange account passwords encrypted with AES-256-GCM
   - Location: `app/utils/crypto.py`
   - Encryption key: `EXCHANGE_ENCRYPTION_KEY` environment variable

3. **Connection Pooling**: Manages Exchange connections efficiently across requests
   - Location: `app/services/exchange/connection_pool.py`
   - Reuses connections to same Exchange account

4. **Webhook Listener**: Worker process subscribes to Exchange events
   - Runs in separate container (`webhook-worker`)
   - Location: `app/services/exchange/webhook_listener.py`

5. **Audit Logging**: All API requests logged with details (user, endpoint, status, timestamp)
   - Middleware: `app/core/middlewares.py` (HttpAuditLogMiddleware)
   - Model: `app/models/admin.py` (HttpLog)

6. **Email Templates**: Dynamically create emails with variable substitution
   - Service: `app/services/exchange/template_service.py`
   - Supports variables like `{{recipient_name}}`

7. **Task Queue (ARQ)**: Asynchronous job processing using Redis
   - Worker: `app/tasks/worker.py` (runs as `arq-worker` container)
   - Used for: Sending emails, delivering webhooks, periodic sync tasks
   - Pool management: `app/core/arq_pool.py`

8. **Structured Logging**: Production-ready logging with context injection
   - Location: `app/core/logging.py`
   - Uses `structlog` for JSON output in prod and colored output in dev
   - Automatically injects `request_id` context

9. **Monitoring**: Prometheus instrumentation
   - Location: `app/core/metrics.py`
   - Exposes `/metrics` endpoint for Prometheus scraping
   - Tracks email success/failure, latency, and circuit breaker states

### Directory Organization

```
app/
├── api/v1/
│   ├── exchange/        # Exchange-specific endpoints
│   ├── base/           # Authentication endpoints
│   ├── users/          # User management
│   ├── roles/          # Role management
│   ├── menus/          # Dashboard menu structure
│   ├── auditlog/       # Audit log endpoints
│   └── health/         # Health check
├── services/exchange/
│   ├── email_service.py        # Email send/receive/search
│   ├── account_service.py      # Account registration & validation
│   ├── webhook_service.py      # Webhook CRUD operations
│   ├── webhook_listener.py     # Subscribe to Exchange events
│   ├── template_service.py     # Email template processing
│   ├── connection_pool.py      # Exchange connection management
│   └── ...
├── models/
│   ├── admin.py        # User, Role, Menu, API, HttpLog
│   ├── exchange.py     # Account, Email, Template, Webhook
│   └── enums.py        # Status enums
├── schemas/
│   ├── exchange.py     # Request/response DTOs for Exchange operations
│   ├── users.py        # User DTOs
│   └── ...
├── core/
│   ├── api_key_auth.py      # API Key validation
│   ├── dependency.py        # FastAPI dependencies
│   ├── exceptions.py        # Custom exception classes
│   ├── middlewares.py       # Request/response middlewares
│   └── init_app.py          # App initialization logic
└── utils/
    ├── crypto.py           # AES encryption/decryption
    ├── jwt_utils.py        # JWT token generation
    ├── password.py         # Password hashing (Argon2)
    └── db_migrate.py       # Database URL parsing
```

## Database Models

Key models in `app/models/`:

- **admin.py**: User, Role, Menu, Api, HttpLog (audit), Dept
- **exchange.py**: Account (Exchange credentials), Email, Template, Webhook, Contact
- **webhook.py**: WebhookEvent (subscription records)
- **base.py**: TimeStampModel (common timestamps)

Relationships:
- User → many Api (API keys)
- Account → many Email, Template, Webhook
- Webhook → many WebhookEvent (historical subscriptions)

## Environment Variables

Key variables configured in `.env`:

```
# Exchange Configuration
EXCHANGE_SERVER=              # Exchange server hostname
EXCHANGE_DOMAIN=              # Domain name
EXCHANGE_EMAIL_SUFFIX=        # Email suffix for service accounts
EXCHANGE_ENCRYPTION_KEY=      # 32-byte key for password encryption

# Database
DATABASE_URL=mysql://user:pass@host:port/db

# Application
SECRET_KEY=                   # For JWT tokens
CORS_ORIGINS=http://localhost:3000

# Deployment
ENV=dev|prod
PORT=8000
WORKERS=2
```

## Testing Strategy

1. **Unit Tests**: Test services and utilities in isolation
   - Location: `tests/unit/`
   - Use pytest fixtures for mocking

2. **Integration Tests**: Test API endpoints with real/mock database
   - Location: `tests/integration/`
   - Excluded from CI by default (can be slow)

3. **Database Tests**: Use separate test database
   - Configuration: `pytest.ini`
   - Test database: `exchange_test`

## API Design Patterns

1. **Request/Response Pattern**:
   - All API responses follow standard format with status/data/message
   - Validation errors return 422 with detail schema

2. **Pagination**:
   - Query params: `skip`, `limit`
   - Returns paginated list with total count

3. **Soft Deletes**:
   - Models have `is_deleted` field
   - Queries filter by `is_deleted=False` by default

4. **Authentication**:
   - API endpoints require `X-Api-Key` header
   - Dashboard endpoints use JWT tokens

## Common Development Tasks

### Adding a New API Endpoint

1. Create schema in `app/schemas/` for request/response
2. Create route handler in `app/api/v1/exchange/` (or appropriate module)
3. Add service method in `app/services/exchange/` if needed
4. Register router in `app/api/__init__.py`
5. Add tests in `tests/` directory

### Adding a New Model/Database Table

1. Define model in `app/models/exchange.py` or `admin.py`
2. Inherit from `TimeStampModel` for common fields
3. Create migration: `aerich migrate --name add_new_model`
4. Review migration in `migrations/` and run: `aerich upgrade`

### Adding Exchange Event Webhook

1. Define webhook type in `app/models/webhook.py`
2. Implement listener in `webhook_listener.py`
3. Add callback handler to process event
4. Store webhook event in database for audit trail

## Docker Compose Services

- **mysql**: MySQL 8.0 database
- **app**: FastAPI application (port 18001, uses `entrypoint.sh`)
- **webhook-worker**: Webhook listener (uses `entrypoint-worker.sh`)
- **arq-worker**: Redis task queue worker (uses `entrypoint-arq.sh`)
- **nginx**: Reverse proxy (port 80)
- **redis**: Redis 7-alpine (for ARQ and rate limiting)

*Note: Worker services have HTTP health checks disabled as they are background processes.*

Access URLs (dev mode):
- Admin Dashboard: `http://localhost`
- API Docs: `http://localhost/docs`
- Direct API: `http://localhost:18001`

## Performance Considerations

1. **Exchange Connections**: Limited by Exchange server, pooling is critical
   - Max connections configured per account
   - Implement timeouts to prevent hanging

2. **Email Operations**: Can be slow (may take seconds)
   - Use background tasks for send operations
   - Store pending emails for recovery on restart

3. **Webhook Events**: Use separate worker process
   - Process events asynchronously
   - Retry failed deliveries

## Security Notes

- Passwords encrypted in database (AES-256-GCM)
- API keys SHA-256 hashed
- JWT tokens used for admin dashboard sessions
- Audit logging for compliance
- Rate limiting supported (Redis-backed)
- CORS configured per environment
