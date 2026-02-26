# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-02-26

### Added
- RESTful API for Exchange/EWS email operations (send, receive, search, reply, forward)
- Email templates with Jinja2 variable substitution
- Webhook subscriptions for Exchange streaming events (NewMail, Created, Modified, Deleted)
- Admin dashboard (Vue 3 + Naive UI) for account and API key management
- API Key authentication with SHA-256 hashing and per-key rate limiting
- AES-256-GCM password encryption for Exchange account credentials
- Redis distributed rate limiter (sliding window via ZSET)
- Redis distributed migration lock for multi-worker safety
- Structured logging via structlog (JSON in production, colored console in dev)
- Prometheus metrics endpoint (`/metrics`)
- ARQ-based async task queue for email sending and webhook delivery
- Docker Compose deployment with Docker Secrets support
- Audit logging middleware with sensitive data masking
- Role-based access control (RBAC) for dashboard users
- Health check endpoints (`/health`, `/health/live`, `/health/ready`)
- Connection pooling for Exchange server connections
- Circuit breaker pattern for Exchange connectivity
