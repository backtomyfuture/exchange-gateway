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
echo "  Vue FastAPI Admin - Starting Server"
echo "=========================================="
echo "  Workers:     ${WORKERS}"
echo "  Bind:        ${BIND}"
echo "  Timeout:     ${TIMEOUT}s"
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
