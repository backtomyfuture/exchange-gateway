
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.lark.handlers.email_handler import EmailActionHandler
from app.models.exchange import ExchangeEmailTemplate

@pytest.fixture
def email_handler():
    return EmailActionHandler()

@pytest.mark.asyncio
async def test_parse_recipients_string(email_handler):
    """Test parsing string recipients"""
    raw = "test1@example.com; test2@example.com, test3@example.com"
    result = await email_handler._parse_recipients(raw)
    assert len(result) == 3
    assert "test1@example.com" in result
    assert "test2@example.com" in result
    assert "test3@example.com" in result

@pytest.mark.asyncio
async def test_parse_recipients_list_mixed(email_handler):
    """Test parsing list of strings and objects"""
    raw = [
        "test1@example.com",
        {"email": "test2@example.com", "name": "User 2"},
        {"id": "ou_123", "name": "User 3"} # Missing email, should trigger lookup
    ]
    
    # Mock contact client
    mock_contact_client = AsyncMock()
    mock_contact_client.batch_get_emails.return_value = {"ou_123": "test3@example.com"}
    
    with patch("app.services.lark.handlers.email_handler.get_contact_client", return_value=mock_contact_client):
        result = await email_handler._parse_recipients(raw, app_id=1)
        
    assert len(result) == 3
    assert "test1@example.com" in result
    assert "test2@example.com" in result
    assert "test3@example.com" in result

@pytest.mark.asyncio
async def test_parse_recipients_empty(email_handler):
    assert await email_handler._parse_recipients(None) == []
    assert await email_handler._parse_recipients([]) == []

@pytest.mark.asyncio
async def test_render_template(email_handler):
    """Test template rendering"""
    # Mock template
    mock_tmpl = MagicMock(spec=ExchangeEmailTemplate)
    mock_tmpl.body = "Hello {{ name }}, check this {{ item }}"
    mock_tmpl.body_type = "text"
    
    mock_filter = AsyncMock()
    mock_filter.first.return_value = mock_tmpl
    
    with patch("app.models.exchange.ExchangeEmailTemplate.filter", return_value=mock_filter):
        # Case 1: Params as dict
        rendered, type_ = await email_handler._render_template(
            "test_tmpl", 
            {"item": "report"}, 
            {"name": "Alice"}
        )
        assert rendered == "Hello Alice, check this report"
        
        # Case 2: Params as string
        rendered, type_ = await email_handler._render_template(
            "test_tmpl", 
            '{"item": "report"}', 
            {"name": "Bob"}
        )
        assert rendered == "Hello Bob, check this report"
