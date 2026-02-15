import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.exchange.email_service import EmailService
from app.schemas.exchange import EmailReplyRequest, EmailForwardRequest
from exchangelib import HTMLBody

@pytest.mark.asyncio
async def test_reply_email_uses_native_method():
    # Setup
    service = EmailService()
    request_body = "<p>My Reply</p>"
    request = EmailReplyRequest(
        account_id=1,
        reference_item_id="item_id",
        body=request_body,
        subject="Re: Subject"
    )
    
    mock_item = MagicMock()
    mock_reply_item = MagicMock()
    mock_item.create_reply.return_value = mock_reply_item
    
    # Mock context manager for get_exchange_connection
    with patch("app.services.exchange.email_service.get_exchange_connection") as mock_conn_ctx:
        mock_conn = AsyncMock()
        mock_conn.account.inbox.get.return_value = mock_item
        mock_conn_ctx.return_value.__aenter__.return_value = mock_conn
        
        # Mock process_inline_images
        with patch("app.services.exchange.format_utils.process_inline_images") as mock_process:
            mock_process.return_value = ("<p>Processed Body</p>", [])
            
            # Mock DB log creation
            with patch("app.models.exchange.ExchangeMailLog.create", new_callable=AsyncMock):
                
                # Execute
                await service.reply_email(request)
                
                # Verify
                # 1. process_inline_images should be called with request.body
                mock_process.assert_called_with(request_body)
                
                # 2. item.create_reply should be called with the PROCESSED body
                # The implementation uses HTMLBody(reply_body_html)
                # We check the arguments passed to create_reply
                args, kwargs = mock_item.create_reply.call_args
                
                # kwargs['body'] should be an HTMLBody instance
                assert isinstance(kwargs['body'], HTMLBody)
                assert kwargs['body'].body == "<p>Processed Body</p>"
                
                # 3. reply_item.send() should be called
                mock_reply_item.send.assert_called_once()

@pytest.mark.asyncio
async def test_forward_email_uses_native_method():
    # Setup
    service = EmailService()
    request_body = "<p>My Forward</p>"
    request = EmailForwardRequest(
        account_id=1,
        reference_item_id="item_id",
        to=["recipient@example.com"],
        body=request_body,
        subject="Fwd: Subject"
    )
    
    mock_item = MagicMock()
    mock_forward_item = MagicMock()
    mock_item.create_forward.return_value = mock_forward_item
    
    with patch("app.services.exchange.email_service.get_exchange_connection") as mock_conn_ctx:
        mock_conn = AsyncMock()
        mock_conn.account = MagicMock()
        mock_conn.account.inbox.get.return_value = mock_item
        mock_conn_ctx.return_value.__aenter__.return_value = mock_conn
        
        with patch("app.services.exchange.format_utils.process_inline_images") as mock_process:
            mock_process.return_value = ("<p>Processed Forward</p>", [])
            
            with patch("app.models.exchange.ExchangeMailLog.create", new_callable=AsyncMock):
                
                # Execute
                await service.forward_email(request)
                
                # Verify
                mock_process.assert_called_with(request_body)
                
                args, kwargs = mock_item.create_forward.call_args
                assert isinstance(kwargs['body'], HTMLBody)
                assert kwargs['body'].body == "<p>Processed Forward</p>"
                
                mock_forward_item.send.assert_called_once()
