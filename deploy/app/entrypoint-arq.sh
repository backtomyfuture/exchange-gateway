#!/bin/bash
set -e

# =============================================================================
# ARQ Task Queue Worker 启动脚本
# 生成缺失的安全密钥，然后启动 ARQ worker
# =============================================================================

echo "=========================================="
echo "  ARQ Worker - Starting"
echo "=========================================="

# 读取 Docker Secrets；没有配置时再回退到环境变量。
read_secret() {
    local name="$1"
    local file_var="${name}_FILE"
    local file_path="${!file_var:-}"
    if [ -n "$file_path" ] && [ -f "$file_path" ]; then
        tr -d '\n' < "$file_path"
    else
        printf '%s' "${!name:-}"
    fi
}

SECRET_KEY="$(read_secret SECRET_KEY)"
EXCHANGE_ENCRYPTION_KEY="$(read_secret EXCHANGE_ENCRYPTION_KEY)"
export SECRET_KEY EXCHANGE_ENCRYPTION_KEY

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
