#!/bin/bash
set -e

# =============================================================================
# Webhook Worker 启动脚本
# 支持密钥自动生成、健康检查
# =============================================================================

echo "=========================================="
echo "  Webhook Worker - Starting"
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

# 等待数据库就绪（如果配置了 DB_HOST）
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at ${DB_HOST}:${DB_PORT:-3306}..."
    
    max_retries=30
    retry_count=0
    
    while ! nc -z "${DB_HOST}" "${DB_PORT:-3306}" 2>/dev/null; do
        retry_count=$((retry_count + 1))
        if [ $retry_count -ge $max_retries ]; then
            echo "ERROR: Database connection timeout after ${max_retries} attempts"
            exit 1
        fi
        echo "  Attempt ${retry_count}/${max_retries}..."
        sleep 2
    done
    
    echo "Database is ready!"
fi

# 仅开发模式允许生成临时密钥；生产必须注入稳定密钥。
if [ "${DEV_MODE:-false}" = "true" ] || [ "${DEV_MODE:-false}" = "1" ] || [ "${DEV_MODE:-false}" = "yes" ]; then
    if [ -z "$SECRET_KEY" ]; then
        echo "WARNING: SECRET_KEY not set, generating one (development only)..."
        export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    fi
    if [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
        echo "WARNING: EXCHANGE_ENCRYPTION_KEY not set, generating one (development only)..."
        # EXCHANGE_ENCRYPTION_KEY 需要 Base64 编码的 32 字节密钥。
        export EXCHANGE_ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")
    fi
elif [ -z "$SECRET_KEY" ] || [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
    echo "ERROR: SECRET_KEY and EXCHANGE_ENCRYPTION_KEY must be provided outside DEV_MODE"
    exit 1
fi

echo "Starting webhook listener..."
echo "=========================================="

# 运行 webhook listener
exec python3 -m app.services.exchange.webhook_listener
