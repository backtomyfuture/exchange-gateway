from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `dept` ADD UNIQUE INDEX `uid_dept_parent__b9d39c` (`parent_id`, `name`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `dept` DROP INDEX `uid_dept_parent__b9d39c`;"""
