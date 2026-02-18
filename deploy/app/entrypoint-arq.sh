#!/bin/bash
set -e

# =============================================================================
# ARQ Task Queue Worker 启动脚本
# 生成缺失的安全密钥，然后启动 ARQ worker
# =============================================================================

echo "=========================================="
echo "  ARQ Worker - Starting"
echo "=========================================="

# 生成缺失的安全密钥
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY not set, generating one..."
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "  Generated SECRET_KEY: ${SECRET_KEY:0:16}..."
fi

if [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
    echo "WARNING: EXCHANGE_ENCRYPTION_KEY not set, generating one..."
    export EXCHANGE_ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")
    echo "  Generated EXCHANGE_ENCRYPTION_KEY: ${EXCHANGE_ENCRYPTION_KEY:0:16}..."
fi

echo "Starting ARQ worker..."
echo "=========================================="

exec python3 -m arq app.tasks.worker.WorkerSettings
