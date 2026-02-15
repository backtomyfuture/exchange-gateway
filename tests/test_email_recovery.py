
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from app.services.exchange.email_service import recover_pending_emails, EmailService
from app.models.exchange import ExchangeMailLog

@pytest.mark.asyncio
async def test_recover_pending_emails_success():
    """
    Test that recover_pending_emails correctly identifies pending logs and adds background tasks.
    """
    # Mock ExchangeMailLog.filter
    mock_log = MagicMock(spec=ExchangeMailLog)
    mock_log.id = 123
    mock_log.status = "pending"
    mock_log.action = "send"
    mock_log.created_at = datetime.now() - timedelta(minutes=30)
    
    # Mock the query set
    mock_filter = AsyncMock()
    mock_filter.all.return_value = [mock_log]
    
    with patch("app.models.exchange.ExchangeMailLog.filter", return_value=mock_filter) as mock_filter_cls, \
         patch("app.core.bgtask.BgTasks.add_task", new_callable=AsyncMock) as mock_add_task:
        
        # Execute
        result = await recover_pending_emails()
        
        # Verify result
        assert result["recovered"] == 1
        assert result["failed"] == 0
        
        # Verify BgTasks.add_task called
        mock_add_task.assert_called_once()
        call_args = mock_add_task.call_args
        assert call_args[1]["log_id"] == 123
        assert call_args[1]["request"] is None

@pytest.mark.asyncio
async def test_recover_pending_emails_exception():
    """
    Test proper error handling during recovery.
    """
    # Mock ExchangeMailLog.filter to raise exception
    mock_log = MagicMock(spec=ExchangeMailLog)
    mock_log.id = 456
    
    mock_filter = AsyncMock()
    mock_filter.all.return_value = [mock_log]
    
    with patch("app.models.exchange.ExchangeMailLog.filter", return_value=mock_filter), \
         patch("app.core.bgtask.BgTasks.add_task", side_effect=Exception("Queue error")):
        
        # Execute
        result = await recover_pending_emails()
        
        # Verify result
        assert result["recovered"] == 0
        assert result["failed"] == 1
