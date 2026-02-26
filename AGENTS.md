# AGENTS.md

## Cursor Cloud specific instructions

### Architecture Overview

Exchange Gateway is an enterprise Exchange/EWS mail gateway consisting of 6 Docker services:
- **mysql**: MySQL 8.0 database (port `13306:3306`)
- **redis**: Redis 7 for task queue and rate limiting
- **app**: FastAPI backend (port `18001:8000`)
- **nginx**: Reverse proxy + Vue 3 SPA frontend (port `80:8080`)
- **arq-worker**: Background task processor (optional)
- **webhook-worker**: Exchange event listener (optional)

### Running the Application (Docker Compose)

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Default admin credentials: `admin` / `123456`

- Dashboard: http://localhost
- API Docs: http://localhost:18001/docs
- Health Check: http://localhost:18001/health

### Docker in Cloud Agent VM

Docker requires special setup in the Cloud Agent VM (nested container environment):

1. Install Docker, `fuse-overlayfs`, and set `iptables-legacy`:
   ```bash
   sudo mkdir -p /etc/docker
   echo '{"storage-driver":"fuse-overlayfs"}' | sudo tee /etc/docker/daemon.json
   sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
   sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
   ```
2. Start the Docker daemon manually: `sudo dockerd &>/tmp/dockerd.log &`
3. Fix socket permissions: `sudo chmod 666 /var/run/docker.sock`

### Linting

- **Backend**: `ruff check app/ tests/ scripts/` (see `CLAUDE.md` for details)
- **Frontend**: `cd web && pnpm lint` (see `CLAUDE.md`)

Pre-existing lint warnings exist in the codebase; these are not regressions.

### Testing

```bash
# Run unit tests inside the app container:
docker compose exec -e DEV_MODE=true app pytest tests/unit/test_crypto.py tests/unit/test_circuit_breaker.py tests/unit/test_email_tasks.py tests/unit/test_webhook_schema.py tests/unit/test_exceptions.py tests/api/test_health.py -v
```

**Known issue**: Some test files (`test_retry.py`, `test_pagination.py`, `test_webhook_listener_refactored.py`, etc.) fail at collection time due to a missing `app/services/__init__.py`. This is a pre-existing codebase issue.

### Gotchas

- The `web/package.json` may need `pnpm.onlyBuiltDependencies` configured for `esbuild`, `vue-demi`, and `es5-ext` to build correctly with pnpm v10+.
- When running `uvicorn --reload` locally (outside Docker), exclude `.docker-data/*` to avoid `PermissionError` from MySQL data files: `--reload-exclude ".docker-data/*"`.
- Redis has no host port mapping in `docker-compose.yml`. For local backend development outside Docker, either add a port mapping or use the container's IP address.
- The `ENV=dev` mode auto-generates `SECRET_KEY` and `EXCHANGE_ENCRYPTION_KEY`; no Exchange server configuration is needed for development.
