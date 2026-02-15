from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ALTER TABLE `exchange_mail_log` ADD `body_type` VARCHAR(10) NOT NULL  COMMENT '正文类型' DEFAULT 'text';
        -- ALTER TABLE `exchange_mail_log` ADD `body` LONGTEXT   COMMENT '邮件正文';
        -- ALTER TABLE `exchange_mail_log` ADD `attachments_payload` JSON   COMMENT '附件数据JSON';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `exchange_mail_log` DROP COLUMN `body_type`;
        ALTER TABLE `exchange_mail_log` DROP COLUMN `body`;
        ALTER TABLE `exchange_mail_log` DROP COLUMN `attachments_payload`;"""
