from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExchangeTimeoutError
from app.schemas.exchange import EmailListRequest
from app.services.exchange.email_service import EmailService


@pytest.mark.asyncio
async def test_list_emails_turns_executor_timeout_into_gateway_504():
    """A stalled large page must fail before the reverse proxy timeout."""
    service = EmailService()
    exchange_connection = AsyncMock()
    exchange_connection.account = MagicMock()

    with (
        patch(
            "app.services.exchange.email_service.get_exchange_connection",
            return_value=exchange_connection,
        ),
        patch(
            "app.services.exchange.email_service.run_sync_with_timeout",
            new=AsyncMock(side_effect=TimeoutError),
        ) as run_sync,
        pytest.raises(ExchangeTimeoutError, match="获取邮件列表超时"),
    ):
        await service.list_emails(EmailListRequest(account_id=1, limit=50))

    run_sync.assert_awaited_once()
