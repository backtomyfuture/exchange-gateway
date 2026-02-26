# ... (imports and aggressive mocking same as before) ...
import asyncio
import binascii
import gzip
import importlib.util
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# AGGRESSIVE MOCKING START
# =============================================================================
def mock_module(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


# Create hierarchy
app_module = mock_module("app")
mock_module("app.log")
mock_module("app.core")
mock_module("app.core.bgtask")
mock_module("app.core.dependency")
mock_module("app.schemas")
mock_module("app.schemas.exchange")
mock_module("app.models")
mock_module("app.models.exchange")

# Ensure traversing works for patch
app_services = mock_module("app.services")
app_module.services = app_services

app_services_exchange = mock_module("app.services.exchange")
app_services.exchange = app_services_exchange

sys.modules["app.log"].logger = MagicMock()


class MockModel:
    def __init__(self, **kwargs):
        pass

    @classmethod
    async def create(cls, **kwargs):
        m = MagicMock()
        m.id = 1
        return m


sys.modules["app.models.exchange"].ExchangeMailLog = MockModel


class MockSchema:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


sys.modules["app.schemas.exchange"].EmailSyncItem = MockSchema
sys.modules["app.schemas.exchange"].EmailItem = MockSchema
sys.modules["app.schemas.exchange"].EmailListRequest = MockSchema
sys.modules["app.schemas.exchange"].EmailSendRequest = MockSchema
sys.modules["app.schemas.exchange"].EmailSearchRequest = MockSchema
sys.modules["app.schemas.exchange"].FolderItem = MockSchema
sys.modules["app.schemas.exchange"].EmailAttachment = MockSchema

# Mock exchangelib dependencies
mock_exchangelib = mock_module("exchangelib")
mock_exchangelib_errors = mock_module("exchangelib.errors")
mock_exchangelib_items = mock_module("exchangelib.items")


class ErrorInvalidSyncStateDataError(Exception):
    pass


class TransportError(Exception):
    pass


class ErrorTimeoutExpiredError(Exception):
    pass


class ErrorFolderNotFoundError(Exception):
    pass


mock_exchangelib_errors.ErrorInvalidSyncStateData = ErrorInvalidSyncStateDataError
mock_exchangelib_errors.TransportError = TransportError
mock_exchangelib_errors.ErrorTimeoutExpired = ErrorTimeoutExpiredError
mock_exchangelib_errors.ErrorFolderNotFound = ErrorFolderNotFoundError

mock_exchangelib_items.SEND_AND_SAVE_COPY = "SendAndSaveCopy"
mock_exchangelib_items.SEND_ONLY = "SendOnly"

mock_exchangelib.FileAttachment = MagicMock()
mock_exchangelib.HTMLBody = MagicMock()
mock_exchangelib.Message = MagicMock()

# Mock connection pool
app_services_exchange_connection_pool = mock_module("app.services.exchange.connection_pool")
app_services_exchange.connection_pool = app_services_exchange_connection_pool
app_services_exchange_connection_pool.get_exchange_connection = MagicMock()

# =============================================================================
# IMPORT TARGET
# =============================================================================
sys.path.append(".")

service_path = "app/services/exchange/email_service.py"
spec = importlib.util.spec_from_file_location("app.services.exchange.email_service", service_path)
email_service_module = importlib.util.module_from_spec(spec)
sys.modules["app.services.exchange.email_service"] = email_service_module
app_services_exchange.email_service = email_service_module

try:
    spec.loader.exec_module(email_service_module)
except Exception as e:
    print(f"Failed to load module: {e}")
    raise

EmailService = email_service_module.EmailService

# =============================================================================
# TEST CLASS
# =============================================================================


class TestSyncErrorHandling(unittest.TestCase):
    def setUp(self):
        self.service = EmailService()
        self.mock_request = MagicMock()
        self.mock_request.account_id = 123
        self.mock_request.folder = "INBOX"
        self.mock_request.sync_state = "bad_state_string"
        self.mock_request.limit = 10
        self.mock_request.only_fields = None

    @patch("app.services.exchange.email_service.get_exchange_connection")
    def test_sync_state_errors(self, mock_get_conn_patch):
        mock_conn = MagicMock()
        mock_folder = MagicMock()
        mock_conn.account.inbox = mock_folder

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_conn
        async_cm.__aexit__.return_value = None

        mock_get_conn_patch.return_value = async_cm

        exceptions = [
            (binascii.Error("Incorrect padding"), "binascii.Error"),
            (gzip.BadGzipFile("Not a gzipped file"), "gzip.BadGzipFile"),
            (ErrorInvalidSyncStateDataError("Invalid state"), "ErrorInvalidSyncStateData"),
            (ValueError("Some other value error"), "ValueError"),
        ]

        async def run_test():
            for exc, name in exceptions:
                print(f"Testing exception: {name}")

                mock_folder.sync_items.side_effect = exc

                with patch("asyncio.get_running_loop") as mock_loop:
                    mock_loop_instance = MagicMock()
                    mock_loop.return_value = mock_loop_instance

                    def side_effect_run(executor, func, *args):
                        return func(*args)

                    mock_loop_instance.run_in_executor.side_effect = side_effect_run

                    # We expect the exception to be CAUGHT and returned as a dict
                    response = await self.service.sync_emails(self.mock_request)

                    print(f"Response: {response}")

                    self.assertFalse(response["success"])
                    self.assertIn("Invalid sync_state", response["message"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
