#!/bin/bash
set -e

# =============================================================================
# Exchange Gateway - Entrypoint
# Reads secrets from Docker Secrets files, then starts Gunicorn.
# =============================================================================

# --- Helper: read secret from file or env var ---
read_secret() {
    local name="$1"
    local file_var="${name}_FILE"
    local file_path="${!file_var}"
    if [ -n "$file_path" ] && [ -f "$file_path" ]; then
        cat "$file_path" | tr -d '\n'
    else
        echo "${!name}"
    fi
}

# --- Load secrets ---
SECRET_KEY=$(read_secret SECRET_KEY)
EXCHANGE_ENCRYPTION_KEY=$(read_secret EXCHANGE_ENCRYPTION_KEY)
DB_PASSWORD=$(read_secret DB_PASSWORD)

# Auto-generate dev secrets if missing
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "WARNING: SECRET_KEY not set, auto-generated (dev only)"
fi
if [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
    EXCHANGE_ENCRYPTION_KEY=$(python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())")
    echo "WARNING: EXCHANGE_ENCRYPTION_KEY not set, auto-generated (dev only)"
fi

export SECRET_KEY EXCHANGE_ENCRYPTION_KEY

# --- Build DATABASE_URL from components if not set ---
if [ -z "$DATABASE_URL" ] && [ -z "$MYSQL_URL" ]; then
    _host="${DB_HOST:-mysql}"
    _port="${DB_PORT:-3306}"
    _name="${DB_NAME:-exchange_gateway}"
    _user="${DB_USER:-root}"
    _pass="${DB_PASSWORD:-}"
    export DATABASE_URL="mysql://${_user}:${_pass}@${_host}:${_port}/${_name}"
fi

# --- Config ---
APP_MODULE="${APP_MODULE:-app:app}"
WORKERS="${WORKERS:-1}"
ACTUAL_PORT="${PORT:-8000}"
BIND="0.0.0.0:${ACTUAL_PORT}"
WORKER_CLASS="${WORKER_CLASS:-uvicorn.workers.UvicornWorker}"
TIMEOUT="${TIMEOUT:-120}"
GRACEFUL_TIMEOUT="${GRACEFUL_TIMEOUT:-30}"
KEEP_ALIVE="${KEEP_ALIVE:-5}"

echo "=========================================="
echo "  Exchange Gateway - Starting Server"
echo "=========================================="
echo "  Workers:     ${WORKERS}"
echo "  Bind:        ${BIND}"
echo "  Timeout:     ${TIMEOUT}s"
echo "  DB Host:     ${DB_HOST:-(from URL)}"
echo "=========================================="

# --- Wait for database ---
URL="${MYSQL_URL:-$DATABASE_URL}"
if [ -n "$URL" ] && [ -z "$DB_HOST" ]; then
    DB_HOST=$(echo "$URL" | sed -e 's|.*@||' -e 's|/.*||' -e 's|:.*||')
    DB_PORT=$(echo "$URL" | grep -o ':[0-9]\+' | tail -n1 | cut -d: -f2)
fi
DB_PORT="${DB_PORT:-3306}"

if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at ${DB_HOST}:${DB_PORT}..."
    retries=0
    while ! nc -z "${DB_HOST}" "${DB_PORT}" 2>/dev/null; do
        retries=$((retries + 1))
        [ $retries -ge 30 ] && echo "ERROR: DB timeout" && exit 1
        echo "  Attempt ${retries}/30..."
        sleep 2
    done
    echo "Database is ready!"
fi

# --- Validate Exchange config (skip in DEV_MODE) ---
if [ "${DEV_MODE:-false}" != "true" ] && [ "${DEV_MODE:-false}" != "1" ]; then
    if [ -z "$EXCHANGE_SERVER" ] || [ -z "$EXCHANGE_DOMAIN" ] || [ -z "$EXCHANGE_EMAIL_SUFFIX" ]; then
        echo "ERROR: Exchange configuration incomplete (set EXCHANGE_SERVER, EXCHANGE_DOMAIN, EXCHANGE_EMAIL_SUFFIX)"
        exit 1
    fi
fi

# --- Database migration ---
if [ "${AUTO_MIGRATE:-true}" = "true" ] || [ "${AUTO_MIGRATE:-true}" = "1" ]; then
    echo "Running database migration..."
    python -m app.utils.db_migrate || echo "Warning: Migration failed, will retry in app startup"
fi

# --- Start ---
exec gunicorn "${APP_MODULE}" \
    --workers "${WORKERS}" \
    --worker-class "${WORKER_CLASS}" \
    --bind "${BIND}" \
    --timeout "${TIMEOUT}" \
    --graceful-timeout "${GRACEFUL_TIMEOUT}" \
    --keep-alive "${KEEP_ALIVE}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
