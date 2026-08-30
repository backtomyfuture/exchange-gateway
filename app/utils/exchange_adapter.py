import ssl

from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

from app.log import logger
from app.settings import settings


class LegacySSLAdapter(HTTPAdapter):
    """
    自定义 SSL Adapter，用于解决与旧版 Exchange 服务器的兼容性问题。
    默认仍然执行证书链和主机名校验；不安全模式只能显式开启。
    """

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        if settings.EXCHANGE_CA_FILE or settings.EXCHANGE_CA_DATA:
            ctx.load_verify_locations(
                cafile=settings.EXCHANGE_CA_FILE or None,
                cadata=settings.EXCHANGE_CA_DATA or None,
            )

        if settings.EXCHANGE_TLS_INSECURE:
            logger.error("EXCHANGE_TLS_INSECURE=true: EWS TLS certificate and hostname validation is disabled")
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            pool_kwargs.setdefault("assert_hostname", False)
        else:
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            # Let urllib3 derive the hostname from the request and discard
            # any insecure override supplied by a caller.
            pool_kwargs.pop("assert_hostname", None)

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

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )
