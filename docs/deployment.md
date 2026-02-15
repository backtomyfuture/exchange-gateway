# Deployment Guide

This guide covers production deployment of exchange-gateway.

## Production Requirements

- Linux server with root access
- Docker & Docker Compose
- SSL certificate (Let's Encrypt or purchased)
- Exchange/Office 365 account

## Deployment Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/f148002/exchange-gateway.git
cd exchange-gateway

# Create production secrets directory
sudo mkdir -p /etc/exchange-gateway/secrets

# Setup SSL certificates
mkdir -p ssl
# Place your certificate files:
#   ssl/exchange.crt
#   ssl/exchange.key
```

### 3. Environment Configuration

```bash
# Copy environment file
cp .env.example .env

# Edit production settings
nano .env
```

Key production variables:

```bash
# Required
EXCHANGE_SERVER=your-exchange-server.com
EXCHANGE_DOMAIN=your-domain.com
EXCHANGE_ENCRYPTION_KEY=generate-a-secure-32-byte-key

# Security
DEV_MODE=false
WEBHOOK_ALLOW_PRIVATE_URLS=false

# Database
DATABASE_URL=mysql://app:password@mysql:3306/exchange

# Ports
NGINX_PORT=80
NGINX_SSL_PORT=443
```

### 4. Setup Secrets

```bash
# Run setup script (requires root)
sudo ./scripts/setup-secrets.sh
```

### 5. Start Services

```bash
# Build and start
docker compose up -d --build

# Check status
docker compose ps
```

### 6. Verify Deployment

```bash
# Check health
curl https://localhost:9998/api/v1/exchange/health

# View logs
docker compose logs -f
```

## SSL Configuration

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to ssl directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/exchange.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/exchange.key
```

### Using Purchased Certificate

Simply place your certificate and key files in the `ssl/` directory.

## Backup & Recovery

### Database Backup

```bash
# Backup database
docker compose exec mysql mysqldump -u root -p exchange > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Restore database
docker compose exec -T mysql -u root -p exchange < backup_20240101.sql
```

## Monitoring

### Health Check

```bash
curl https://your-server:9998/api/v1/exchange/health
```

### Log Management

```bash
# View logs
docker compose logs -f

# Rotate logs
docker compose logs --tail=100 > logs.txt
```

## Security Checklist

- [ ] Change default admin password
- [ ] Use strong `EXCHANGE_ENCRYPTION_KEY` (32+ random characters)
- [ ] Configure firewall (only allow ports 80, 443)
- [ ] Enable fail2ban for brute force protection
- [ ] Regular database backups
- [ ] Keep Docker images updated

## Troubleshooting

### Common Issues

#### Connection Timeout

Check if Exchange server is reachable:
```bash
docker compose exec app ping your-exchange-server.com
```

#### SSL Certificate Errors

Verify certificate files:
```bash
openssl x509 -in ssl/exchange.crt -text -noout
```

#### Database Connection Issues

Check database logs:
```bash
docker compose logs mysql
```
