"""
AccountService 单元测试
测试账户管理和 API Key 管理功能
注意：仅测试独立于数据库的功能
"""

from unittest.mock import patch

from app.services.exchange.account_service import AccountService, get_account_service

# ========================================
# 基础功能测试
# ========================================


def test_get_account_service_singleton():
    """测试账户服务单例模式"""
    svc1 = get_account_service()
    svc2 = get_account_service()
    assert svc1 is svc2


def test_account_service_initialization():
    """测试服务初始化"""
    svc = AccountService()
    assert svc is not None
    assert svc._crypto is None  # 延迟加载


def test_account_service_crypto_property():
    """测试加密模块懒加载"""
    with patch("app.services.exchange.account_service.get_crypto") as mock_crypto:
        mock_crypto_instance = object()
        mock_crypto.return_value = mock_crypto_instance

        svc = AccountService()
        crypto = svc.crypto

        assert crypto is mock_crypto_instance
        mock_crypto.assert_called_once()


# ========================================
# API Key 工具函数测试
# ========================================


def test_generate_api_key():
    """测试 API Key 生成"""
    from app.utils.crypto import generate_api_key

    key = generate_api_key()

    assert key is not None
    assert len(key) > 20  # 应该足够长


def test_generate_api_key_uniqueness():
    """测试 API Key 唯一性"""
    from app.utils.crypto import generate_api_key

    keys = set()
    for _ in range(100):
        keys.add(generate_api_key())

    assert len(keys) == 100  # 所有 key 应该唯一


def test_hash_api_key():
    """测试 API Key 哈希"""
    from app.utils.crypto import hash_api_key

    key = "test_api_key_12345"
    hashed = hash_api_key(key)

    assert hashed is not None
    assert hashed != key  # 哈希值不应等于原值
    assert len(hashed) == 64  # SHA-256 产生 64 字符十六进制


def test_hash_api_key_consistency():
    """测试 API Key 哈希一致性"""
    from app.utils.crypto import hash_api_key

    key = "consistent_key"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)

    assert hash1 == hash2  # 相同输入应产生相同哈希
