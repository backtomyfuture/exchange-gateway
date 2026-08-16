import ssl
from unittest.mock import patch

from app.settings import settings
from app.utils.exchange_adapter import LegacySSLAdapter


def _build_ssl_context():
    adapter = LegacySSLAdapter()
    adapter.init_poolmanager(connections=1, maxsize=1)
    return adapter.poolmanager.connection_pool_kw["ssl_context"]


def test_exchange_tls_defaults_to_certificate_and_hostname_validation():
    with patch.object(settings, "EXCHANGE_TLS_INSECURE", False):
        context = _build_ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_exchange_tls_insecure_mode_is_explicit():
    with patch.object(settings, "EXCHANGE_TLS_INSECURE", True):
        context = _build_ssl_context()

    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False
