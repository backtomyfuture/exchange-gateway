from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE `webhook_subscription`
    MODIFY COLUMN `secret` VARCHAR(2048) NOT NULL COMMENT '签名密钥 (HMAC SHA256)';
CREATE INDEX `idx_auditlog_created_at` ON `auditlog` (`created_at`);
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP INDEX `idx_auditlog_created_at` ON `auditlog`;
ALTER TABLE `webhook_subscription`
    MODIFY COLUMN `secret` VARCHAR(100) NOT NULL COMMENT '签名密钥 (HMAC SHA256)';
"""
