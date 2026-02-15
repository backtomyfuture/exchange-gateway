# Getting Started

This guide will help you get exchange-gateway up and running in development mode.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- MySQL 8.0 (included in Docker Compose)
- Exchange/Office 365 account

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway
```

### 2. Setup Development Secrets

```bash
./scripts/setup-secrets.sh --dev
```

This creates a `.secrets/` directory with encryption keys for development.

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your Exchange server details:

```bash
EXCHANGE_SERVER=your-exchange-server.com
EXCHANGE_DOMAIN=your-domain.com
DEV_MODE=true
```

### 4. Start Services

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 5. Access the Services

| Service | URL |
|---------|-----|
| Admin Dashboard | https://localhost:9998 |
| API Docs | https://localhost:9998/docs |
| MySQL | localhost:3306 |

Default admin credentials:
- Username: admin
- Password: admin123

## Adding an Exchange Account

1. Login to the admin dashboard
2. Go to Exchange > Accounts
3. Click "Add Account"
4. Fill in your Exchange credentials:
   - Email: your.email@company.com
   - Password: your exchange password
   - Server: autodetect or specify EWS endpoint

## Testing the API

### Get API Key

1. Go to Exchange > API Keys
2. Create a new API key with desired permissions

### Send a Test Email

```bash
curl -k -X POST "https://localhost:9998/api/v1/exchange/emails/send" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "to": ["test@example.com"],
    "subject": "Test",
    "body": "Hello from exchange-gateway!"
  }'
```

## Development Tips

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest tests/ -v
```

### Viewing Logs

```bash
# View all service logs
docker compose -f docker-compose.dev.yml logs -f

# View specific service
docker compose -f docker-compose.dev.yml logs -f app
docker compose -f docker-compose.dev.yml logs -f webhook-worker
```

### Database Migrations

```bash
# Generate migration
aerich migrate --name add_new_field

# Apply migrations
aerich migrate
```

## Next Steps

- Read the [API Reference](api.md) for detailed endpoint documentation
- Set up [Webhooks](webhook.md) for real-time event notifications
- Configure [Production Deployment](deployment.md) for production use
