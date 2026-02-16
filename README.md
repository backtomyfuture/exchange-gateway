# exchange-gateway

[![License](https://img.shields.io/github/license/f148002/exchange-gateway)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Last Commit](https://img.shields.io/github/last-commit/f148002/exchange-gateway)](https://github.com/f148002/exchange-gateway)

**Enterprise-grade Exchange/EWS mail gateway built with FastAPI.** Provides secure REST API for email operations and a complete admin dashboard.

## ⚡ Quick Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/template/exchange-gateway?referralCode=f148002)

## Features

- **RESTful API**: Send, receive, search emails via API Key authentication
- **Email Templates**: Create and manage email templates with variable substitution
- **Webhook Support**: Subscribe to Exchange events (NewMail, Created, Modified, etc.)
- **Admin Dashboard**: Account management, API keys, templates, audit logs
- **Security**: AES-256-GCM password encryption, API Key hashing, key rotation
- **Docker Deployment**: Production-ready Docker Compose configuration

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Exchange/Office 365 account

### Deployment

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

## Access

| Service | URL |
|---------|-----|
| Admin Dashboard | `http://localhost:80` |
| API Docs | `http://localhost:80/docs` |
| App Direct | `http://localhost:18001` |
| Health Check | `http://localhost:18001/api/v1/exchange/health` |

## API Usage

### Send Email

```bash
curl -k -X POST "https://your-server:9998/api/v1/exchange/emails/send" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "to": ["recipient@example.com"],
    "subject": "Test Email",
    "body": "<p>Email content</p>",
    "body_type": "html"
  }'
```

### Get Email Details

```bash
curl -k -X GET "https://your-server:9998/api/v1/exchange/emails/{message_id}" \
  -H "X-Api-Key: YOUR_API_KEY"
```

### Webhook Events

Subscribe to Exchange events via Webhook:

```bash
curl -k -X POST "https://your-server:9998/api/v1/exchange/webhooks" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-callback-server.com/webhook",
    "events": ["NewMailEvent"],
    "secret": "your-webhook-secret"
  }'
```

## Documentation

- [Getting Started](docs/getting-started.md)
- [Deployment Guide](docs/deployment.md)
- [API Reference](docs/api.md)
- [Webhook Guide](docs/webhook.md)
- [Configuration](docs/configuration.md)

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Tortoise ORM, exchangelib
- **Frontend**: Vue 3, Vite, Naive UI, Pinia
- **Database**: MySQL 8.0
- **Deployment**: Docker, Nginx

## Directory Structure

```
exchange-gateway/
├── app/                    # FastAPI application
│   ├── api/v1/exchange/    # Exchange API routes
│   ├── models/             # Data models
│   └── services/exchange/  # Email service layer
├── web/                    # Vue3 admin dashboard
├── tests/                  # Test suite
├── docs/                   # Documentation
├── docker/                 # Docker configurations
├── scripts/                # Deployment scripts
└── migrations/             # Database migrations
```

## Security

- **Password Encryption**: Exchange account passwords encrypted with AES-256-GCM
- **API Key**: SHA-256 hashed, displayed only once on creation
- **Secrets**: Production passwords stored in `/etc/exchange-gateway/secrets/`

### Key Rotation

```bash
python scripts/rotate_key.py --old-key "old-key" --new-key "new-key" --dry-run
python scripts/rotate_key.py --old-key "old-key" --new-key "new-key"
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

This project is based on [vue-fastapi-admin](https://github.com/mizhexiaoxiao/vue-fastapi-admin) (MIT License).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
