import os
import typing

from pydantic import model_validator
from pydantic_settings import BaseSettings

# =============================================================================
# DEV_MODE: 开发模式
# 设置环境变量 DEV_MODE=true 可启用零配置开发模式，无需设置 SECRET_KEY 等配置
# 警告：请勿在生产环境使用 DEV_MODE！
# =============================================================================
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

# 开发模式默认值（仅用于本地开发，请勿在生产环境使用！）
_DEV_SECRET_KEY = "dev-secret-key-do-not-use-in-production-environment"
_DEV_DB_PASSWORD = "dev_password"


def get_secret(secret_name: str, default: str = "") -> str:
    """
    从文件读取 secret，支持 Docker Secrets 模式。

    优先检查 {SECRET_NAME}_FILE 环境变量指定的文件路径，
    如果文件存在则读取其内容作为 secret 值。
    否则回退到直接读取 {SECRET_NAME} 环境变量或使用默认值。

    Args:
        secret_name: secret 名称（如 DB_PASSWORD）
        default: 默认值

    Returns:
        secret 值
    """
    file_env = f"{secret_name}_FILE"
    if file_path := os.getenv(file_env):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            pass
    return os.getenv(secret_name, default)


class Settings(BaseSettings):
    VERSION: str = "1.0.0"
    APP_TITLE: str = "Exchange Email Server"
    PROJECT_NAME: str = "Exchange Email Server"
    APP_DESCRIPTION: str = "Exchange邮箱服务器，提供各种接口"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    # DEV_MODE 时自动启用 DEBUG，否则默认关闭
    DEBUG: bool = DEV_MODE or os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    # Webhook URL 安全策略：开发环境默认允许私网地址，生产环境默认禁止
    WEBHOOK_ALLOW_PRIVATE_URLS: bool = os.getenv(
        "WEBHOOK_ALLOW_PRIVATE_URLS", "true" if DEV_MODE else "false"
    ).lower() in ("true", "1", "yes")

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    # 日志目录：优先使用环境变量，否则使用默认值
    # Docker 环境建议设置 LOGS_ROOT=/var/log/app
    LOGS_ROOT: str = os.getenv("LOGS_ROOT", os.path.join(BASE_DIR, "app/logs"))

    # SECRET_KEY: DEV_MODE 时使用内置默认值，否则必须从环境变量或 Docker Secrets 读取
    # 生成方式: openssl rand -hex 32
    SECRET_KEY: str = get_secret("SECRET_KEY", _DEV_SECRET_KEY if DEV_MODE else "")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day

    # Database configuration: DEV_MODE 时使用默认开发配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "admin")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", _DEV_DB_PASSWORD if DEV_MODE else "")
    DB_NAME: str = os.getenv("DB_NAME", "vue_fastapi_admin")

    # 数据库连接池配置
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "20"))

    # =============================================================================
    # Exchange 邮件服务配置
    # =============================================================================
    EXCHANGE_SERVER: str = os.getenv("EXCHANGE_SERVER", "")
    EXCHANGE_DOMAIN: str = os.getenv("EXCHANGE_DOMAIN", "")
    EXCHANGE_EMAIL_SUFFIX: str = os.getenv("EXCHANGE_EMAIL_SUFFIX", "")
    # 凭据加密密钥（生产环境必须设置）
    # 生成方式: python -c "from app.utils.crypto import generate_encryption_key; print(generate_encryption_key())"
    EXCHANGE_ENCRYPTION_KEY: str = get_secret("EXCHANGE_ENCRYPTION_KEY", "")
    # API 速率限制（每分钟请求数）
    EXCHANGE_API_RATE_LIMIT: int = int(os.getenv("EXCHANGE_API_RATE_LIMIT", "100"))
    # API Key 默认过期天数
    EXCHANGE_API_KEY_EXPIRE_DAYS: int = int(os.getenv("EXCHANGE_API_KEY_EXPIRE_DAYS", "365"))
    # EWS Streaming 连接超时（分钟），EWS 文档建议连接最长 30 分钟
    EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES: int = int(os.getenv("EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES", "30"))
    # Streaming 异常重连等待（秒），仅在异常时生效
    EXCHANGE_STREAM_ERROR_RETRY_SECONDS: int = int(os.getenv("EXCHANGE_STREAM_ERROR_RETRY_SECONDS", "5"))

    TORTOISE_ORM: dict = {}

    @model_validator(mode="after")
    def validate_and_build_config(self):
        """验证配置并构建 TORTOISE_ORM"""
        # DEV_MODE 警告
        if DEV_MODE:
            import warnings

            warnings.warn("\n⚠️  DEV_MODE 已启用！使用内置默认配置。\n⚠️  请勿在生产环境使用 DEV_MODE！\n", UserWarning)

        # 验证 SECRET_KEY 是否已配置（DEV_MODE 时已有默认值，不会触发）
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY 未配置！请通过环境变量 SECRET_KEY 或 SECRET_KEY_FILE 设置。\n"
                "生成方式: openssl rand -hex 32\n"
                "提示：本地开发可设置 DEV_MODE=true 使用默认配置"
            )

        # 验证 EXCHANGE_ENCRYPTION_KEY 是否已配置（生产环境必须）
        if not DEV_MODE and not self.EXCHANGE_ENCRYPTION_KEY:
            raise ValueError(
                "EXCHANGE_ENCRYPTION_KEY 未配置！\n"
                "生成方式: python -c 'from app.utils.crypto import generate_encryption_key; print(generate_encryption_key())'\n"
                "提示：本地开发可设置 DEV_MODE=true 跳过此验证"
            )

        if not 1 <= self.EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES <= 30:
            raise ValueError("EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES 必须在 1 到 30 之间")

        if self.EXCHANGE_STREAM_ERROR_RETRY_SECONDS < 0:
            raise ValueError("EXCHANGE_STREAM_ERROR_RETRY_SECONDS 不能小于 0")

        # 使用 get_secret 函数获取密码，支持 Docker Secrets
        db_password = get_secret("DB_PASSWORD", self.DB_PASSWORD)

        self.TORTOISE_ORM = {
            "connections": {
                # PostgreSQL configuration
                # Install with: tortoise-orm[asyncpg]
                # "postgres": {
                #     "engine": "tortoise.backends.asyncpg",
                #     "credentials": {
                #         "host": os.getenv("DB_HOST", self.DB_HOST),
                #         "port": int(os.getenv("DB_PORT", str(self.DB_PORT))),
                #         "user": os.getenv("DB_USER", self.DB_USER),
                #         "password": db_password,
                #         "database": os.getenv("DB_NAME", self.DB_NAME),
                #     },
                # },
                # SQLite configuration (fallback)
                # "sqlite": {
                #     "engine": "tortoise.backends.sqlite",
                #     "credentials": {"file_path": f"{self.BASE_DIR}/db.sqlite3"},
                # },
                # MySQL/MariaDB configuration
                # Install with: tortoise-orm[asyncmy]
                "mysql": {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": os.getenv("DB_HOST", self.DB_HOST),
                        "port": int(os.getenv("DB_PORT", "3306")),
                        "user": os.getenv("DB_USER", self.DB_USER),
                        "password": db_password,
                        "database": os.getenv("DB_NAME", self.DB_NAME),
                        "minsize": self.DB_POOL_MIN_SIZE,
                        "maxsize": self.DB_POOL_MAX_SIZE,
                        "charset": "utf8mb4",
                    },
                },
            },
            "apps": {
                "models": {
                    "models": ["app.models", "aerich.models"],
                    "default_connection": "mysql",
                },
            },
            "use_tz": False,  # Whether to use timezone-aware datetimes
            "timezone": "Asia/Shanghai",  # Timezone setting
        }
        return self

    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


settings = Settings()
