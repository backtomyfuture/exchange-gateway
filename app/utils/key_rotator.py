"""
加密密钥轮换工具
用于在更换 EXCHANGE_ENCRYPTION_KEY 时重新加密所有邮箱账户密码
"""

from app.log import logger
from app.models.exchange import ExchangeAccount
from app.models.webhook import WebhookSubscription
from app.utils.crypto import CredentialCrypto


class KeyRotator:
    """
    密钥轮换器

    用于安全地将所有加密数据从旧密钥迁移到新密钥。

    使用示例：
        rotator = KeyRotator(old_key, new_key)
        result = await rotator.rotate_all_accounts()
        print(f"成功轮换 {result['success']}/{result['total']} 个账户")
    """

    def __init__(self, old_key: str, new_key: str):
        """
        初始化轮换器

        Args:
            old_key: 旧的加密密钥（Base64 编码）
            new_key: 新的加密密钥（Base64 编码）
        """
        self.old_crypto = CredentialCrypto(old_key)
        self.new_crypto = CredentialCrypto(new_key)

    async def rotate_account(self, account: ExchangeAccount) -> dict:
        """
        轮换单个账户的密码加密

        Args:
            account: 邮箱账户对象

        Returns:
            dict: {"success": bool, "email": str, "error": Optional[str]}
        """
        try:
            # 使用旧密钥解密
            password = self.old_crypto.decrypt(account.encrypted_password)

            # 使用新密钥重新加密
            new_encrypted = self.new_crypto.encrypt(password)

            # 更新数据库
            account.encrypted_password = new_encrypted
            await account.save()

            logger.info(f"密钥轮换成功: {account.email}")
            return {"success": True, "email": account.email, "error": None}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"密钥轮换失败: {account.email}, 错误: {error_msg}")
            return {"success": False, "email": account.email, "error": error_msg}

    async def rotate_all_accounts(self, dry_run: bool = False) -> dict:
        """
        轮换所有账户的密码加密

        Args:
            dry_run: 如果为 True，只验证旧密钥能否解密，不实际更新

        Returns:
            dict: {
                "total": int,
                "success": int,
                "failed": int,
                "failures": list[dict],
                "dry_run": bool
            }
        """
        accounts = await ExchangeAccount.all()

        total = len(accounts)
        success_count = 0
        failures = []

        logger.info(f"开始密钥轮换，共 {total} 个账户，dry_run={dry_run}")

        for account in accounts:
            if dry_run:
                # 只验证解密是否成功
                try:
                    self.old_crypto.decrypt(account.encrypted_password)
                    logger.info(f"[dry-run] 验证成功: {account.email}")
                    success_count += 1
                except Exception as e:
                    failures.append({"email": account.email, "error": str(e)})
            else:
                result = await self.rotate_account(account)
                if result["success"]:
                    success_count += 1
                else:
                    failures.append({"email": result["email"], "error": result["error"]})

        result = {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "failures": failures,
            "dry_run": dry_run,
        }

        if dry_run:
            logger.info(f"[dry-run] 验证完成: {success_count}/{total} 成功")
        else:
            logger.info(f"密钥轮换完成: {success_count}/{total} 成功")

        return result

    async def rotate_webhook_secret(self, webhook: WebhookSubscription) -> dict:
        """Re-encrypt one webhook signing secret."""
        try:
            secret = self.old_crypto.decrypt(webhook.secret)
            webhook.secret = self.new_crypto.encrypt(secret)
            await webhook.save()
            logger.info(f"Webhook 密钥轮换成功: {webhook.url}")
            return {"success": True, "url": webhook.url, "error": None}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Webhook 密钥轮换失败: {webhook.url}, 错误: {error_msg}")
            return {"success": False, "url": webhook.url, "error": error_msg}

    async def rotate_all_webhook_secrets(self, dry_run: bool = False) -> dict:
        """Rotate every persisted webhook signing secret."""
        webhooks = await WebhookSubscription.all()
        total = len(webhooks)
        success_count = 0
        failures = []

        logger.info(f"开始 Webhook 密钥轮换，共 {total} 个订阅，dry_run={dry_run}")
        for webhook in webhooks:
            if dry_run:
                try:
                    self.old_crypto.decrypt(webhook.secret)
                    logger.info(f"[dry-run] Webhook 验证成功: {webhook.url}")
                    success_count += 1
                except Exception as e:
                    failures.append({"url": webhook.url, "error": str(e)})
            else:
                result = await self.rotate_webhook_secret(webhook)
                if result["success"]:
                    success_count += 1
                else:
                    failures.append({"url": result["url"], "error": result["error"]})

        return {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "failures": failures,
            "dry_run": dry_run,
        }

    async def rotate_all(self, dry_run: bool = False) -> dict:
        """Rotate both Exchange account passwords and webhook secrets."""
        account_result = await self.rotate_all_accounts(dry_run=dry_run)
        webhook_result = await self.rotate_all_webhook_secrets(dry_run=dry_run)
        result = {
            "total": account_result["total"] + webhook_result["total"],
            "success": account_result["success"] + webhook_result["success"],
            "failed": account_result["failed"] + webhook_result["failed"],
            "failures": account_result["failures"] + webhook_result["failures"],
            "dry_run": dry_run,
            "accounts": account_result,
            "webhooks": webhook_result,
        }
        logger.info(
            f"全部加密数据轮换完成: {result['success']}/{result['total']} 成功，"
            f"失败 {result['failed']}"
        )
        return result

    def verify_keys(self) -> dict:
        """
        验证新旧密钥是否有效

        Returns:
            dict: {"old_key_valid": bool, "new_key_valid": bool}
        """
        test_data = "test_password_verification_string"

        old_valid = True
        new_valid = True

        try:
            encrypted = self.old_crypto.encrypt(test_data)
            decrypted = self.old_crypto.decrypt(encrypted)
            old_valid = decrypted == test_data
        except Exception:
            old_valid = False

        try:
            encrypted = self.new_crypto.encrypt(test_data)
            decrypted = self.new_crypto.decrypt(encrypted)
            new_valid = decrypted == test_data
        except Exception:
            new_valid = False

        return {"old_key_valid": old_valid, "new_key_valid": new_valid}


async def rotate_encryption_key(old_key: str, new_key: str, dry_run: bool = False) -> dict:
    """
    便捷函数：轮换加密密钥

    Args:
        old_key: 旧的加密密钥
        new_key: 新的加密密钥
        dry_run: 是否只验证不修改

    Returns:
        轮换结果
    """
    rotator = KeyRotator(old_key, new_key)

    # 先验证密钥
    key_check = rotator.verify_keys()
    if not key_check["old_key_valid"]:
        return {"error": "旧密钥无效", "key_check": key_check}
    if not key_check["new_key_valid"]:
        return {"error": "新密钥无效", "key_check": key_check}

    # 执行轮换
    return await rotator.rotate_all(dry_run=dry_run)
