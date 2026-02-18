from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `exchange_mail_log` ADD `request_body` JSON NULL COMMENT '序列化的发送请求体，用于ARQ重试';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `exchange_mail_log` DROP COLUMN `request_body`;"""
