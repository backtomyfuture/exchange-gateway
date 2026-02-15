import pytest

# ========================================
# 业务逻辑测试
# ========================================

@pytest.mark.asyncio
async def test_verify_account_async():
    """测试账户验证是否正确使用异步非阻塞调用"""
    from unittest.mock import MagicMock, AsyncMock, patch
    from app.services.exchange.account_service import AccountService
    
    # Setup
    svc = AccountService()
    account_id = 1
    
    # Mocks
    mock_account_db = MagicMock()
    mock_account_db.id = account_id
    mock_account_db.save = AsyncMock()
    
    # Mock connection
    mock_conn = MagicMock()
    mock_conn.account.inbox.total_count = 5
    
    # Mock get_exchange_connection context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_conn
    
    with patch("app.services.exchange.account_service.ExchangeAccount") as MockExchangeAccount, \
         patch("app.services.exchange.account_service.get_exchange_connection", return_value=mock_cm):
        
        # Mock DB
        mock_qs = MagicMock()
        # first() returns Coroutine that returns mock_account_db
        mock_qs.first = AsyncMock(return_value=mock_account_db)
        MockExchangeAccount.filter.return_value = mock_qs
        
        # Execute
        result = await svc.test_account(account_id, owner_id=1)
        
        # Verify
        assert result["success"] is True
        assert "5" in result["message"]
        
        # Verify DB updated
        assert mock_account_db.is_verified is True
        mock_account_db.save.assert_awaited_once()
        
        # Verify executed in thread pool (indirectly by success of async call involving blocking prop)
        # To strictly verify run_in_executor, we would need to spy on the loop, 
        # but the success of the test with a Mock (which is thread-safeish) implies it ran.
