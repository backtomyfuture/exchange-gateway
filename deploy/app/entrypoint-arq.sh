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

# 仅开发模式允许生成临时密钥；生产必须注入稳定密钥。
if [ "${DEV_MODE:-false}" = "true" ] || [ "${DEV_MODE:-false}" = "1" ] || [ "${DEV_MODE:-false}" = "yes" ]; then
    if [ -z "$SECRET_KEY" ]; then
        echo "WARNING: SECRET_KEY not set, generating one (development only)..."
        export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    fi
    if [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
        echo "WARNING: EXCHANGE_ENCRYPTION_KEY not set, generating one (development only)..."
        export EXCHANGE_ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")
    fi
elif [ -z "$SECRET_KEY" ] || [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
    echo "ERROR: SECRET_KEY and EXCHANGE_ENCRYPTION_KEY must be provided outside DEV_MODE"
    exit 1
fi

echo "Starting ARQ worker..."
echo "=========================================="

exec python3 -m arq app.tasks.worker.WorkerSettings
