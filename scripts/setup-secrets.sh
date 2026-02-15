#!/bin/bash
# =============================================================================
# Exchange 邮件网关 Secrets 设置脚本
#
# 功能：统一生成 Docker Secrets 文件，支持开发和生产环境
#
# 用法：
#   生产环境 (需 sudo):  sudo ./scripts/setup-secrets.sh
#   开发环境:           ./scripts/setup-secrets.sh --dev
#
# 路径：
#   生产环境: /etc/exchange/secrets/
#   开发环境: ./.secrets/
# =============================================================================

set -e

# 获取脚本所在目录的上一级目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 默认模式为生产环境
MODE="prod"

# 检查参数
if [[ "$1" == "--dev" ]]; then
    MODE="dev"
fi

echo "=========================================="
if [[ "$MODE" == "prod" ]]; then
    echo "  Secrets 设置 (生产环境)"
    SECRETS_DIR="/etc/exchange/secrets"
    
    # 生产环境检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        echo "错误：生产环境部署请使用 sudo 运行此脚本"
        echo "用法：sudo $0"
        exit 1
    fi
else
    echo "  Secrets 设置 (开发环境)"
    SECRETS_DIR="$PROJECT_DIR/.secrets"
fi
echo "=========================================="
echo ""
echo "Secrets 目录: $SECRETS_DIR"
echo ""

# 创建目录
if [ -d "$SECRETS_DIR" ] && [[ "$MODE" == "dev" ]]; then
    echo "警告：目录已存在"
    # 开发环境不强制删除，避免误操作，但在自动化脚本中可能需要
    # 这里保持简单，直接继续，文件会被覆盖
fi

mkdir -p "$SECRETS_DIR"
# 生产环境设置严格权限，开发环境设置当前用户可读写
if [[ "$MODE" == "prod" ]]; then
    chmod 700 "$SECRETS_DIR"
else
    chmod 755 "$SECRETS_DIR"
fi

# -----------------------------------------------------------------------------
# 密码获取逻辑
# -----------------------------------------------------------------------------

MYSQL_ROOT_PASSWORD=""
MYSQL_PASSWORD=""
EXCHANGE_ENCRYPTION_KEY=""

if [[ "$MODE" == "prod" ]]; then
    # 生产环境：交互式输入
    echo "请输入以下密码（输入时不会显示）："
    echo ""
    
    while [ -z "$MYSQL_ROOT_PASSWORD" ]; do
        read -sp "MySQL Root 密码: " MYSQL_ROOT_PASSWORD
        echo ""
    done

    while [ -z "$MYSQL_PASSWORD" ]; do
        read -sp "MySQL 用户密码 (应用连接数据库使用): " MYSQL_PASSWORD
        echo ""
    done
    
    # 生产环境自动生成随机加密密钥
    EXCHANGE_ENCRYPTION_KEY=$(openssl rand -base64 32)
    
else
    # 开发环境：使用默认密码
    echo "使用默认开发密码..."
    MYSQL_ROOT_PASSWORD="dev_root_password"
    MYSQL_PASSWORD="dev_password"
    EXCHANGE_ENCRYPTION_KEY=$(openssl rand -base64 32)
    # 也可以使用固定的开发密钥，方便调试，这里为了安全性习惯还是随机生成，
    # 或者如果需要固定，可以使用: EXCHANGE_ENCRYPTION_KEY="dev-encryption-key-base64-encoded-value"
    # 但随机生成并不影响开发启动（只要不重启且需要保留加密数据）。
    # 为了方便开发重启不丢失解密能力（如果不持久化secrets），其实开发环境固定更好？
    # 但脚本每次运行都会重新生成，如果重新运行脚本，数据库里的老数据（如果加密了）就解不开了。
    # 考虑到开发环境通常重置数据，随机也没问题。
fi

# -----------------------------------------------------------------------------
# 生成文件
# -----------------------------------------------------------------------------

echo "正在生成 Secrets 文件..."

# MySQL 密码
echo -n "$MYSQL_ROOT_PASSWORD" > "$SECRETS_DIR/mysql_root_password"
echo -n "$MYSQL_PASSWORD" > "$SECRETS_DIR/mysql_password"
# db_password 复用 mysql_password
echo -n "$MYSQL_PASSWORD" > "$SECRETS_DIR/db_password"

# JWT Secret Key (总是随机生成)
SECRET_KEY=$(openssl rand -hex 32)
echo -n "$SECRET_KEY" > "$SECRETS_DIR/secret_key"

# Exchange 加密密钥
echo -n "$EXCHANGE_ENCRYPTION_KEY" > "$SECRETS_DIR/exchange_encryption_key"

# -----------------------------------------------------------------------------
# 权限设置
# -----------------------------------------------------------------------------

if [[ "$MODE" == "prod" ]]; then
    # 生产环境：所有者可读写，其他人不可读（根据之前的 setup-secrets.sh，设为 644 是为了让容器映射读取，
    # 实际上 docker bind mount 不会改变文件权限，宿主机 644 是安全的，只要目录是 700）
    chmod 644 "$SECRETS_DIR"/*
else
    # 开发环境
    chmod 644 "$SECRETS_DIR"/*
fi

echo ""
echo "=========================================="
echo "  设置完成！"
echo "=========================================="
echo ""
echo "文件列表："
ls -la "$SECRETS_DIR"
echo ""

if [[ "$MODE" == "prod" ]]; then
    echo "下一步：运行 docker-compose up -d"
else
    echo "下一步：docker-compose -f docker-compose.dev.yml up -d"
    echo "警告：开发环境密码仅供测试使用，请勿用于生产！"
fi
echo ""
