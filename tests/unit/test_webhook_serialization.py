import pytest
import asyncio
from unittest.mock import Mock
from app.services.exchange.webhook_listener import BlockingAccountListener

class MockEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockId:
    def __init__(self, id, changekey):
        self.id = id
        self.changekey = changekey

def test_serialize_exchange_event_raw():
    # Setup
    listener = BlockingAccountListener(1, asyncio.Queue())
    
    item_id = MockId("item-id-123", "ck-1")
    folder_id = MockId("folder-id-456", "ck-2")
    
    event = MockEvent(
        watermark="watermark-xyz",
        timestamp="2024-02-12T12:00:00",
        unread_count=10,
        item_id=item_id,
        folder_id=folder_id,
        parent_folder_id=None,
        # Emulate internal/callable attrs that should be ignored
        _private="secret",
        some_method=lambda: None
    )
    
    # Execute
    data = listener._serialize_exchange_event(event)
    
    # Verify Flat Structure
    assert data["watermark"] == "watermark-xyz"
    assert data["timestamp"] == "2024-02-12T12:00:00"
    assert data["unread_count"] == 10
    
    # Verify Object Recursion
    assert data["item_id"] == {"id": "item-id-123", "changekey": "ck-1"}
    assert data["folder_id"] == {"id": "folder-id-456", "changekey": "ck-2"}
    
    # Verify Filtering
    assert "_private" not in data
    assert "some_method" not in data
