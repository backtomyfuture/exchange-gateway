# Webhook Guide

Learn how to configure webhooks to receive real-time notifications from Exchange events.

## Overview

Webhooks allow your application to receive real-time notifications when mailbox events occur in Exchange. This enables:

- Real-time email processing
- Automated workflows
- Push-based integrations

## Supported Events

| Event | Description |
|-------|-------------|
| `NewMailEvent` | New email received in Inbox |
| `CreatedEvent` | New item created (email, calendar, etc.) |
| `ModifiedEvent` | Item modified (read status, flag, etc.) |
| `DeletedEvent` | Item deleted |
| `MovedEvent` | Item moved to another folder |
| `CopiedEvent` | Item copied |

## Creating a Webhook

### Request

```bash
curl -X POST "https://your-server:9998/api/v1/exchange/webhooks" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-callback-server.com/webhook",
    "events": ["NewMailEvent"],
    "secret": "your-webhook-secret",
    "account_id": 1,
    "enabled": true
  }'
```

### Response

```json
{
  "code": 200,
  "msg": "Success",
  "data": {
    "id": 1,
    "url": "https://your-callback-server.com/webhook",
    "events": ["NewMailEvent"],
    "account_id": 1,
    "enabled": true,
    "secret": "whsec_xxxxxxxxxxxx"  // Save this - shown only once!
  }
}
```

**Important**: The secret is shown only once upon creation. Make sure to save it securely.

## Webhook Payload

When an event occurs, your endpoint will receive a POST request:

### Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` |
| `X-Exchange-Event` | Event type (e.g., `NewMailEvent`) |
| `X-Exchange-Signature` | HMAC-SHA256 signature of the payload |

### Body

```json
{
  "account_id": 1,
  "event": "NewMailEvent",
  "event_type": "NewMailEvent",
  "item_id": {
    "id": "AAMkAD...",
    "changekey": "CQAAAB..."
  },
  "folder_id": {
    "id": "AQMkAD...",
    "changekey": "AQAAAQ..."
  },
  "watermark": "abc123",
  "unread_count": 1
}
```

## Verifying Signatures

Always verify the webhook signature to ensure requests are authentic:

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# Usage
@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Exchange-Signature")
    
    if not verify_signature(body, signature, WEBHOOK_SECRET):
        return {"error": "Invalid signature"}, 401
    
    # Process webhook...
```

## Recommended Processing Flow

1. **Verify Signature**: Check HMAC-SHA256 signature
2. **Filter Events**: Only process events you care about
3. **Idempotency**: Deduplicate using `account_id + event + item_id`
4. **Respond Quickly**: Return 200 within 5 seconds
5. **Async Processing**: Do heavy processing in background

## Listing Webhooks

```bash
curl -X GET "https://your-server:9998/api/v1/exchange/webhooks" \
  -H "X-Api-Key: YOUR_API_KEY"
```

## Updating a Webhook

```bash
curl -X PUT "https://your-server:9998/api/v1/exchange/webhooks/1" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://new-callback-server.com/webhook",
    "events": ["NewMailEvent", "CreatedEvent"],
    "enabled": true
  }'
```

## Deleting a Webhook

```bash
curl -X DELETE "https://your-server:9998/api/v1/exchange/webhooks/1" \
  -H "X-Api-Key: YOUR_API_KEY"
```

## Best Practices

1. **Always verify signatures** - Prevent spoofed requests
2. **Respond quickly** - Process async, return 200 immediately
3. **Handle retries** - Implement idempotency for reliability
4. **Use HTTPS** - Protect sensitive data in transit
5. **Rotate secrets** - Update webhook secrets periodically

## Troubleshooting

### Webhook Not Received

- Check firewall allows incoming requests
- Verify URL is publicly accessible
- Ensure server responds within timeout

### Signature Verification Fails

- Use raw body bytes, not parsed JSON
- Verify secret matches exactly
- Check HMAC algorithm (SHA256)

### Duplicate Events

- Implement idempotency keys
- Store processed event IDs
- Add deduplication window (e.g., 24 hours)
