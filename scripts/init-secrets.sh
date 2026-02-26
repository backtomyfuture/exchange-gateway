#!/usr/bin/env bash
# =============================================================================
# Exchange Gateway - Initialize Docker Secrets
# Run once before first deployment to generate secure secrets.
# =============================================================================
set -euo pipefail

SECRETS_DIR="$(cd "$(dirname "$0")/.." && pwd)/secrets"

mkdir -p "$SECRETS_DIR"

generate_if_missing() {
    local file="$1"
    local generator="$2"
    local desc="$3"

    if [ -f "$SECRETS_DIR/$file" ] && [ -s "$SECRETS_DIR/$file" ]; then
        echo "  [skip] $desc already exists: $file"
    else
        eval "$generator" > "$SECRETS_DIR/$file"
        chmod 600 "$SECRETS_DIR/$file"
        echo "  [new]  $desc generated: $file"
    fi
}

echo "Initializing secrets in $SECRETS_DIR ..."
echo ""

generate_if_missing "secret_key" \
    "openssl rand -hex 32" \
    "JWT Secret Key"

generate_if_missing "exchange_encryption_key" \
    "python3 -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode(), end=\"\")'" \
    "Exchange Encryption Key"

generate_if_missing "db_password" \
    "openssl rand -base64 24 | tr -d '\n'" \
    "Database Password"

echo ""
echo "Done. Secrets directory: $SECRETS_DIR"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Edit .env with your Exchange server config"
echo "  3. docker compose --profile local-db --profile local-redis up -d"
