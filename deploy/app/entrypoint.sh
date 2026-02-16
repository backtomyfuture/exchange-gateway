#!/bin/bash
set -e

# =============================================================================
# FastAPI 应用启动脚本
# 支持信号处理、优雅关闭、健康检查
# =============================================================================

# 配置
APP_MODULE="${APP_MODULE:-app:app}"
WORKERS="${WORKERS:-4}"
BIND="${BIND:-0.0.0.0:8000}"
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
echo "=========================================="
echo "Database Configuration Debug:"
echo "  MYSQL_URL:   ${MYSQL_URL:-(not set)}"
echo "  DATABASE_URL: ${DATABASE_URL:-(not set)}"
echo "  DB_HOST:     ${DB_HOST:-(not set)}"
echo "=========================================="

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

# 生成缺失的安全密钥
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY not set, generating one..."
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "  Generated SECRET_KEY: ${SECRET_KEY:0:16}..."
fi

if [ -z "$EXCHANGE_ENCRYPTION_KEY" ]; then
    echo "WARNING: EXCHANGE_ENCRYPTION_KEY not set, generating one..."
    # 注意：EXCHANGE_ENCRYPTION_KEY 需要 Base64 编码的 32 字节密钥
    export EXCHANGE_ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")
    echo "  Generated EXCHANGE_ENCRYPTION_KEY: ${EXCHANGE_ENCRYPTION_KEY:0:16}..."
fi

# 验证 Exchange 配置（DEV_MODE 时跳过）
if [ "${DEV_MODE:-false}" != "true" ] && [ "${DEV_MODE:-false}" != "1" ] && [ "${DEV_MODE:-false}" != "yes" ]; then
    if [ -z "$EXCHANGE_SERVER" ] || [ -z "$EXCHANGE_DOMAIN" ] || [ -z "$EXCHANGE_EMAIL_SUFFIX" ]; then
        echo "ERROR: Exchange configuration is incomplete!"
        [ -z "$EXCHANGE_SERVER" ] && echo "  - EXCHANGE_SERVER is required"
        [ -z "$EXCHANGE_DOMAIN" ] && echo "  - EXCHANGE_DOMAIN is required"
        [ -z "$EXCHANGE_EMAIL_SUFFIX" ] && echo "  - EXCHANGE_EMAIL_SUFFIX is required"
        echo ""
        echo "Please configure these environment variables in your .env file:"
        echo "  EXCHANGE_SERVER=your-exchange-server"
        echo "  EXCHANGE_DOMAIN=your-domain"
        echo "  EXCHANGE_EMAIL_SUFFIX=@your-domain.com"
        exit 1
    fi
    echo "Exchange configuration validated: ${EXCHANGE_SERVER}"
else
    echo "WARNING: DEV_MODE enabled, Exchange configuration validation skipped"
fi

# 执行数据库迁移（在启动 gunicorn 之前）
# 只有在 AUTO_MIGRATE=true 或未设置时才执行
if [ "${AUTO_MIGRATE:-true}" = "true" ] || [ "${AUTO_MIGRATE:-true}" = "1" ]; then
    echo "Running database migration..."
    python -m app.utils.db_migrate || echo "Warning: Migration failed, will retry in app startup"
fi

# 使用 exec 替换当前进程，确保信号能正确传递到 gunicorn
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
