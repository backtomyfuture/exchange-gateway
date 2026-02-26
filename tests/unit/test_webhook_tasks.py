from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_deliver_skips_already_delivered(init_test_db):
    from app.models.webhook import WebhookDelivery, WebhookSubscription
    from app.tasks.webhook_tasks import deliver_webhook_task

    sub = await WebhookSubscription.create(
        url="https://example.com/hook",
        secret="s",
        account_id=1,
        events=["NewMailEvent"],
        folders=[],
        is_active=True,
        created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id,
        event_type="NewMailEvent",
        payload={"type": "NewMailEvent"},
        status="delivered",
    )
    result = await deliver_webhook_task({"job_try": 1}, delivery.id)
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_deliver_marks_delivered_on_success(init_test_db):
    from app.models.webhook import WebhookDelivery, WebhookSubscription
    from app.tasks.webhook_tasks import deliver_webhook_task

    sub = await WebhookSubscription.create(
        url="https://example.com/hook",
        secret="s",
        account_id=1,
        events=["NewMailEvent"],
        folders=[],
        is_active=True,
        created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id,
        event_type="NewMailEvent",
        payload={"type": "NewMailEvent"},
        status="pending",
    )
    with patch("app.tasks.webhook_tasks._http_post_webhook") as mock_post:
        mock_post.return_value = None
        result = await deliver_webhook_task({"job_try": 1}, delivery.id)

    assert result["success"] is True
    await delivery.refresh_from_db()
    assert delivery.status == "delivered"


@pytest.mark.asyncio
async def test_deliver_marks_dead_after_max_retries(init_test_db):
    import httpx

    from app.models.webhook import WebhookDelivery, WebhookSubscription
    from app.tasks.webhook_tasks import deliver_webhook_task

    sub = await WebhookSubscription.create(
        url="https://example.com/hook",
        secret="s",
        account_id=1,
        events=["NewMailEvent"],
        folders=[],
        is_active=True,
        created_by=1,
    )
    delivery = await WebhookDelivery.create(
        subscription_id=sub.id,
        event_type="NewMailEvent",
        payload={"type": "NewMailEvent"},
        status="pending",
    )
    with patch("app.tasks.webhook_tasks._http_post_webhook") as mock_post:
        mock_post.side_effect = httpx.ConnectError("refused")
        await deliver_webhook_task({"job_try": 5}, delivery.id)

    await delivery.refresh_from_db()
    assert delivery.status == "dead"
