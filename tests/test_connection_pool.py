from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.exchange.connection_pool import (
    ExchangeConnection,
    ExchangeConnectionPool,
    get_exchange_connection,
)


@pytest.fixture
def mock_crypto():
    crypto = MagicMock()
    crypto.decrypt.return_value = "decrypted_password"
    return crypto


@pytest.fixture
def connection_pool(mock_crypto):
    # Reset singleton manually
    ExchangeConnectionPool._instance = None
    pool = ExchangeConnectionPool()
    pool._crypto = mock_crypto

    # We must patch the singleton getter to return this instance
    # The module has `_connection_pool` variable but also `get_connection_pool()` func
    # We will patch `get_connection_pool` where it is used.

    yield pool

    ExchangeConnectionPool._instance = None


@pytest.fixture
def mock_account_db():
    account = MagicMock()
    account.id = 1
    account.email = "test@example.com"
    account.is_active = True
    account.encrypted_password = "encrypted"
    account.server = "mail.example.com"
    account.domain = "EXAMPLE"
    account.username = "user"
    return account


@pytest.mark.asyncio
async def test_get_connection_creates_new(connection_pool, mock_account_db):
    """Test creating a new connection"""

    # We patch get_connection_pool in the MODULE where get_exchange_connection is defined (or imported from)
    # get_exchange_connection calls get_connection_pool()

    with (
        patch("app.services.exchange.connection_pool.get_connection_pool", return_value=connection_pool),
        patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter,
        patch("app.services.exchange.connection_pool.Account") as mock_account,
        patch("app.services.exchange.connection_pool.Configuration"),
        patch("app.services.exchange.connection_pool.Credentials"),
    ):
        # Mock DB
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=mock_account_db)

        # Mock Exchange Account
        mock_exch_acc = MagicMock()
        mock_account.return_value = mock_exch_acc
        mock_exch_acc.inbox.total_count = 10

        # Call the context manager
        # It calls get_connection_pool() -> returns our connection_pool mock
        # Then connection_pool.get_connection(1)
        async with get_exchange_connection(1) as conn:
            assert isinstance(conn, ExchangeConnection)
            assert conn.account_id == 1
            assert await conn.is_healthy() is True
            assert 1 in connection_pool._pools


@pytest.mark.asyncio
async def test_get_connection_reuse(connection_pool, mock_account_db):
    """Test reusing existing connection"""

    with (
        patch("app.services.exchange.connection_pool.get_connection_pool", return_value=connection_pool),
        patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter,
        patch("app.services.exchange.connection_pool.Account") as mock_account,
        patch("app.services.exchange.connection_pool.Configuration"),
        patch("app.services.exchange.connection_pool.Credentials"),
    ):
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=mock_account_db)

        mock_account.return_value = MagicMock()

        # 1. Create
        async with get_exchange_connection(1) as conn1:
            pass

        # 2. Reuse
        async with get_exchange_connection(1) as conn2:
            assert conn1 is conn2


@pytest.mark.asyncio
async def test_remove_connection(connection_pool, mock_account_db):
    """Test removing connection"""

    with (
        patch("app.services.exchange.connection_pool.get_connection_pool", return_value=connection_pool),
        patch("app.services.exchange.connection_pool.ExchangeAccount.filter") as mock_filter,
        patch("app.services.exchange.connection_pool.Account"),
        patch("app.services.exchange.connection_pool.Configuration"),
        patch("app.services.exchange.connection_pool.Credentials"),
    ):
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=mock_account_db)

        async with get_exchange_connection(1):
            pass

        await connection_pool.close_account_connections(1)
        assert 1 not in connection_pool._pools
