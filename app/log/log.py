import os
import sys

from loguru import logger as loguru_logger

from app.settings import settings


class Loggin:
    def __init__(self) -> None:
        self.debug = settings.DEBUG
        self.level = "DEBUG" if self.debug else "INFO"
        self.logs_root = settings.LOGS_ROOT

    def setup_logger(self):
        loguru_logger.remove()

        # 日志格式
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "<magenta>{extra}</magenta>"
        )

        # 简洁格式（用于文件）
        file_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message} | {extra}"

        # 控制台输出
        loguru_logger.add(
            sink=sys.stdout,
            level=self.level,
            format=log_format,
            colorize=True,
        )

        try:
            # 确保日志目录存在
            os.makedirs(self.logs_root, exist_ok=True)

            # 文件输出（INFO 级别及以上）
            loguru_logger.add(
                sink=os.path.join(self.logs_root, "app.log"),
                level="INFO",
                format=file_format,
                rotation="100 MB",  # 文件大小超过 100MB 自动轮转
                retention="30 days",  # 保留 30 天的日志
                compression="gz",  # 压缩旧日志
                encoding="utf-8",
                enqueue=True,  # 异步写入，提高性能
            )

            # 错误日志单独输出
            loguru_logger.add(
                sink=os.path.join(self.logs_root, "error.log"),
                level="ERROR",
                format=file_format,
                rotation="50 MB",
                retention="90 days",
                compression="gz",
                encoding="utf-8",
                enqueue=True,
            )
        except (PermissionError, OSError) as e:
            # 如果无法写入日志文件（例如 Docker 权限问题），则仅输出到控制台
            print(f"Warning: Failed to setup file logging due to permission error: {e}")

        return loguru_logger


loggin = Loggin()
logger = loggin.setup_logger()
