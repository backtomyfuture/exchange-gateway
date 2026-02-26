"""
凭据加密工具
使用 AES-256-GCM 加密敏感信息（如邮箱密码）
"""
import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialCrypto:
    """
    AES-256-GCM 凭据加密类
    
    使用说明：
    - 加密后的数据格式：base64(nonce + ciphertext)
    - nonce 为 12 字节随机数
    - 主密钥从环境变量或配置中获取
    """

    NONCE_SIZE = 12  # GCM 推荐 nonce 大小
    KEY_SIZE = 32    # AES-256 需要 32 字节密钥

    def __init__(self, encryption_key: str):
        """
        初始化加密器
        
        Args:
            encryption_key: Base64 编码的加密密钥
        """
        if not encryption_key:
            raise ValueError("加密密钥不能为空")

        try:
            self._key = base64.b64decode(encryption_key)
            if len(self._key) != self.KEY_SIZE:
                raise ValueError(f"密钥长度必须为 {self.KEY_SIZE} 字节")
        except Exception as e:
            raise ValueError(f"无效的加密密钥格式: {e}")

        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """
        加密明文
        
        Args:
            plaintext: 要加密的明文字符串
            
        Returns:
            Base64 编码的加密数据（包含 nonce）
        """
        if not plaintext:
            raise ValueError("明文不能为空")

        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        # 将 nonce 和密文拼接后进行 base64 编码
        encrypted_data = base64.b64encode(nonce + ciphertext).decode('utf-8')
        return encrypted_data

    def decrypt(self, encrypted_data: str) -> str:
        """
        解密密文
        
        Args:
            encrypted_data: Base64 编码的加密数据
            
        Returns:
            解密后的明文字符串
        """
        if not encrypted_data:
            raise ValueError("加密数据不能为空")

        try:
            data = base64.b64decode(encrypted_data)
            nonce = data[:self.NONCE_SIZE]
            ciphertext = data[self.NONCE_SIZE:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败: {e}")


@lru_cache(maxsize=1)
def get_crypto() -> CredentialCrypto:
    """
    获取全局加密器实例（单例模式）
    
    Returns:
        CredentialCrypto 实例
    """
    from app.settings import settings
    return CredentialCrypto(settings.EXCHANGE_ENCRYPTION_KEY)


def generate_encryption_key() -> str:
    """
    生成新的加密密钥
    
    Returns:
        Base64 编码的 32 字节随机密钥
    """
    key = os.urandom(CredentialCrypto.KEY_SIZE)
    return base64.b64encode(key).decode('utf-8')


def generate_api_key() -> str:
    """
    生成 API 密钥
    
    Returns:
        32 字节的十六进制字符串
    """
    return os.urandom(32).hex()


def hash_api_key(api_key: str) -> str:
    """
    对 API 密钥进行哈希
    
    Args:
        api_key: 原始 API 密钥
        
    Returns:
        SHA-256 哈希值（十六进制）
    """
    import hashlib
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def verify_api_key_hash(api_key: str, expected_hash: str) -> bool:
    """
    常量时间比较 API 密钥哈希，防止 timing attack。

    Args:
        api_key: 原始 API 密钥
        expected_hash: 数据库中存储的哈希值

    Returns:
        是否匹配
    """
    import hmac

    computed = hash_api_key(api_key)
    return hmac.compare_digest(computed, expected_hash)
