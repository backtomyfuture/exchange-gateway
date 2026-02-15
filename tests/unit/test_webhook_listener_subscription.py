import asyncio

from app.services.exchange.webhook_listener import BlockingAccountListener, WebhookManager
from app.settings.config import settings


class _FakeSubscriptionContext:
    def __init__(self, subscription_id):
        self._subscription_id = subscription_id

    def __enter__(self):
        return self._subscription_id

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeId:
    def __init__(self, value):
        self.id = value


class _FakeEvent:
    def __init__(self, item_id=None, folder_id=None):
        self.item_id = _FakeId(item_id) if item_id else None
        self.folder_id = _FakeId(folder_id) if folder_id else None


class _FakeNotification:
    def __init__(self, events):
        self.events = events


class _FakeInbox:
    def __init__(self, events):
        self._events = events
        self.get_events_calls = 0

    def get_streaming_events(self, subscription_id_or_ids, connection_timeout=1):
        self.get_events_calls += 1
        assert subscription_id_or_ids == "sub-1"
        assert connection_timeout == settings.EXCHANGE_STREAM_CONNECTION_TIMEOUT_MINUTES
        return iter(self._events)


class _FakeAccount:
    def __init__(self):
        self.inbox = _FakeInbox(events=[
            _FakeNotification([_FakeEvent(item_id="item-1"), _FakeEvent(folder_id="folder-1")]),
            _FakeNotification([_FakeEvent(item_id="item-2")]),
        ])
        self.streaming_calls = 0
        self.last_event_types = None

    def streaming_subscription(self, event_types=None):
        self.streaming_calls += 1
        self.last_event_types = event_types
        return _FakeSubscriptionContext("sub-1")


def test_iter_stream_notifications_uses_account_streaming_and_global_events():
    listener = BlockingAccountListener(account_id=1, queue=asyncio.Queue())
    account = _FakeAccount()

    events = list(listener._iter_stream_notifications(account, event_types=["NewMailEvent"]))

    assert len(events) == 3
    assert [e.item_id.id if e.item_id else None for e in events] == ["item-1", None, "item-2"]
    assert account.streaming_calls == 1
    assert account.last_event_types == ["NewMailEvent"]
    assert account.inbox.get_events_calls == 1


class _FakeSub:
    def __init__(self, events, account_id=1):
        self.events = events
        self.account_id = account_id


def test_resolve_exchange_event_types_maps_webhook_event_names():
    subs = [_FakeSub(["NewMail", "Modified"])]
    resolved = WebhookManager._resolve_exchange_event_types(subs)
    assert set(resolved) == {"NewMailEvent", "ModifiedEvent"}


def test_resolve_exchange_event_types_supports_wildcard():
    subs = [_FakeSub(["*"])]
    resolved = WebhookManager._resolve_exchange_event_types(subs)
    assert "NewMailEvent" in resolved
    assert "CreatedEvent" in resolved


def test_resolve_exchange_event_types_defaults_to_new_mail():
    subs = [_FakeSub([])]
    resolved = WebhookManager._resolve_exchange_event_types(subs)
    assert resolved == ["NewMailEvent"]
