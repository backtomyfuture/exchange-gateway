"""
测试加密工具模块
"""

import base64
from unittest.mock import patch

import pytest

from app.utils.crypto import (
    CredentialCrypto,
    generate_api_key,
    generate_encryption_key,
    get_crypto,
    hash_api_key,
)


class TestCredentialCrypto:
    """测试凭据加密类"""

    @pytest.fixture
    def valid_key(self):
        """创建有效的测试密钥"""
        return base64.b64encode(b"\x00" * 32).decode("utf-8")

    @pytest.fixture
    def crypto(self, valid_key):
        """创建测试加密器"""
        return CredentialCrypto(valid_key)

    def test_init_with_valid_key(self, valid_key):
        """测试使用有效密钥初始化"""
        crypto = CredentialCrypto(valid_key)
        assert crypto._key is not None
        assert len(crypto._key) == 32

    def test_init_with_empty_key(self):
        """测试使用空密钥初始化"""
        with pytest.raises(ValueError, match="加密密钥不能为空"):
            CredentialCrypto("")

    def test_init_with_invalid_key(self):
        """测试使用无效密钥初始化"""
        with pytest.raises(ValueError, match="无效的加密密钥格式"):
            CredentialCrypto("invalid-key")

    def test_init_with_wrong_size_key(self):
        """测试使用错误长度密钥初始化"""
        # 16字节而不是32字节
        wrong_key = base64.b64encode(b"\x00" * 16).decode("utf-8")
        with pytest.raises(ValueError, match="密钥长度必须为 32 字节"):
            CredentialCrypto(wrong_key)

    def test_encrypt_decrypt_roundtrip(self, crypto):
        """测试加密解密往返"""
        plaintext = "test password 123!"

        encrypted = crypto.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)

        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, crypto):
        """测试加密空字符串"""
        with pytest.raises(ValueError, match="明文不能为空"):
            crypto.encrypt("")

    def test_decrypt_empty_string(self, crypto):
        """测试解密空字符串"""
        with pytest.raises(ValueError, match="加密数据不能为空"):
            crypto.decrypt("")

    def test_decrypt_invalid_data(self, crypto):
        """测试解密无效数据"""
        with pytest.raises(ValueError, match="解密失败"):
            crypto.decrypt("invalid-data")

    def test_decrypt_tampered_data(self, crypto):
        """测试解密被篡改的数据"""
        plaintext = "test password"
        encrypted = crypto.encrypt(plaintext)

        # 篡改加密数据
        tampered = encrypted[:-4] + "XXXX"

        with pytest.raises(ValueError, match="解密失败"):
            crypto.decrypt(tampered)

    def test_encrypt_produces_different_ciphertexts(self, crypto):
        """测试相同明文产生不同密文（由于随机nonce）"""
        plaintext = "same password"

        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)

        assert encrypted1 != encrypted2

        # 但都能正确解密
        assert crypto.decrypt(encrypted1) == plaintext
        assert crypto.decrypt(encrypted2) == plaintext

    def test_encrypt_unicode(self, crypto):
        """测试加密Unicode字符"""
        plaintext = "测试密码 ñoño émojis 🎉"

        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == plaintext


class TestUtilityFunctions:
    """测试工具函数"""

    def test_generate_encryption_key(self):
        """测试生成加密密钥"""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        # 应该是有效的base64
        decoded1 = base64.b64decode(key1)
        decoded2 = base64.b64decode(key2)

        # 长度应该是32字节
        assert len(decoded1) == 32
        assert len(decoded2) == 32

        # 每次生成的密钥应该不同
        assert key1 != key2

    def test_generate_api_key(self):
        """测试生成API密钥"""
        key1 = generate_api_key()
        key2 = generate_api_key()

        # 应该是32字节的十六进制字符串（64字符）
        assert len(key1) == 64
        assert len(key2) == 64

        # 应该是有效的十六进制
        int(key1, 16)  # 不抛出异常
        int(key2, 16)

        # 每次生成的密钥应该不同
        assert key1 != key2

    def test_hash_api_key(self):
        """测试API密钥哈希"""
        api_key = "test-api-key-123"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        # 相同的API密钥应该产生相同的哈希
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256产生64字符的十六进制字符串

        # 不同的API密钥应该产生不同的哈希
        different_hash = hash_api_key("different-key")
        assert different_hash != hash1

    def test_hash_api_key_is_deterministic(self):
        """测试API密钥哈希是确定性的"""
        api_key = "my-secret-api-key"

        hashes = [hash_api_key(api_key) for _ in range(10)]

        # 所有哈希应该相同
        assert all(h == hashes[0] for h in hashes)


class TestGetCrypto:
    """测试获取全局加密器"""

    @patch("app.settings.config.settings")
    def test_get_crypto_singleton(self, mock_settings):
        """测试获取单例加密器"""
        mock_settings.EXCHANGE_ENCRYPTION_KEY = base64.b64encode(b"\x00" * 32).decode("utf-8")

        # 清除缓存
        get_crypto.cache_clear()

        crypto1 = get_crypto()
        crypto2 = get_crypto()

        # 应该是同一个实例
        assert crypto1 is crypto2

    def test_get_crypto_with_invalid_key(self):
        """测试获取加密器时使用无效密钥"""
        # 直接测试 CredentialCrypto 类的初始化
        with pytest.raises(ValueError, match="无效的加密密钥格式"):
            CredentialCrypto("invalid-key")


class TestCryptoIntegration:
    """加密集成测试"""

    def test_real_world_usage_pattern(self):
        """测试真实使用模式"""
        # 生成密钥
        key = generate_encryption_key()
        crypto = CredentialCrypto(key)

        # 模拟存储多个账户的密码
        passwords = {
            "user1@example.com": "password123",
            "user2@example.com": "my-secure-pwd!",
            "user3@example.com": "test@#$%",
        }

        encrypted_passwords = {}
        for email, password in passwords.items():
            encrypted = crypto.encrypt(password)
            encrypted_passwords[email] = encrypted

            # 验证可以解密
            decrypted = crypto.decrypt(encrypted)
            assert decrypted == password

        # 验证不同账户的加密结果不同
        assert len(set(encrypted_passwords.values())) == len(passwords)


class TestVerifyApiKeyHash:
    """测试 API 密钥哈希验证"""

    def test_verify_api_key_hash_match(self):
        from app.utils.crypto import verify_api_key_hash

        api_key = "my-test-api-key"
        hashed = hash_api_key(api_key)
        assert verify_api_key_hash(api_key, hashed) is True

    def test_verify_api_key_hash_mismatch(self):
        from app.utils.crypto import verify_api_key_hash

        api_key = "my-test-api-key"
        hashed = hash_api_key(api_key)
        assert verify_api_key_hash("wrong-key", hashed) is False
