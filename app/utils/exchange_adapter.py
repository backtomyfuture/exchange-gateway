import ssl

from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

from app.log import logger


class LegacySSLAdapter(HTTPAdapter):
    """
    自定义 SSL Adapter，用于解决与旧版 Exchange 服务器的兼容性问题。
    主要解决 SSLEOFError (protocol violation) 和证书主机名不匹配的问题。
    """

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # 允许 Legacy Renegotiation (OpenSSL 3.0+)
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        else:
            logger.warning("ssl.OP_LEGACY_SERVER_CONNECT 不可用，跳过 legacy renegotiation 兼容设置")

        # 降低安全级别以允许较旧的加密套件 (SECLEVEL=1)
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        except Exception as e:
            logger.warning(f"Could not set ciphers to SECLEVEL=1: {e}")

        # 允许调用方透传 PoolManager 参数，避免与 requests/urllib3 版本演进冲突
        pool_kwargs.setdefault("ssl_context", ctx)
        pool_kwargs.setdefault("assert_hostname", False)

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )
