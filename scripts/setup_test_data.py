
import asyncio
import os
import sys
from tortoise import Tortoise

# Add project root to path
sys.path.append(os.getcwd())

# Set DEV_MODE to use default settings
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.exchange import ExchangeApiKey, ExchangeAccount
from app.utils.crypto import hash_api_key

async def init():
    # Initialize Tortoise
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # User provided key
    raw_key = "665a0eca0796aa573dc91590f07e2a2aa1e82f777e070f07b69383435c45d860"
    target_account_id = 8
    
    print(f"Checking Account ID {target_account_id}...")
    account = await ExchangeAccount.get_or_none(id=target_account_id)
    if account:
        print(f"✅ Account {target_account_id} exists: {account.email}")
    else:
        print(f"❌ Account {target_account_id} does NOT exist in local DB!")
        print("Cannot proceed with real sync test without valid account credentials.")
        # We could create a dummy one but it won't work for real Exchange connection
    
    print(f"\nSetting up API Key...")
    key_hash = hash_api_key(raw_key)
    
    # Check if key exists
    api_key = await ExchangeApiKey.filter(key_hash=key_hash).first()
    if api_key:
        print(f"✅ API Key already exists. ID: {api_key.id}, Permissions: {api_key.permissions}")
        # Update permissions just in case
        api_key.permissions = ["sync", "receive", "send", "search", "read", "delete"]
        api_key.allowed_accounts = [] # Ensure it can access all or add 8
        api_key.is_active = True
        await api_key.save()
        print("Updated permissions.")
    else:
        print("Creating new API Key...")
        await ExchangeApiKey.create(
            name="Test Reproduction Key",
            key_prefix=raw_key[:8],
            key_hash=key_hash,
            permissions=["sync", "receive", "send", "search", "read", "delete"],
            allowed_accounts=[],
            owner_id=1, # Assuming admin user 1 exists
            is_active=True
        )
        print("✅ API Key created.")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(init())
