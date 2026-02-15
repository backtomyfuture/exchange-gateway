import asyncio
import os
import sys

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tortoise import Tortoise
from app.settings.config import settings
from app.models.exchange import ExchangeApiKey, ExchangeAccount
from app.utils.crypto import generate_api_key, hash_api_key

async def main():
    print("Initializing DB connection...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    # 1. Generate a new API Key
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)
    key_prefix = raw_key[:8]
    
    print(f"Generated Key: {raw_key}")
    print(f"Key Prefix: {key_prefix}")
    
    # 2. Check/Create API Key in DB
    key_name = "LocalTestKey"
    
    # Delete existing if any
    await ExchangeApiKey.filter(name=key_name).delete()
    
    # Find an owner (e.g., admin)
    # For now, just use owner_id=1 assuming admin exists, or find first user
    owner_id = 1
    
    api_key = await ExchangeApiKey.create(
        name=key_name,
        key_prefix=key_prefix,
        key_hash=hashed_key,
        permissions=["receive", "read", "sync", "search", "folders", "delete", "send"], # Add all permissions for testing
        allowed_accounts=[], # Empty means all? Or need to specify. Logic usually checks if list is empty or matches.
        # Let's check model comments or controller: "allowed_accounts = fields.JSONField(default=list, description="允许使用的账户ID列表")"
        # Usually empty list implies restriction or no restriction depending on implementation. 
        # Safest is to add the account ID we find.
        owner_id=owner_id,
        is_active=True
    )
    print(f"Created API Key record with ID: {api_key.id}")
    
    # 3. Find a valid Exchange Account
    account = await ExchangeAccount.all().first()
    if not account:
        print("ERROR: No ExchangeAccount found in database. Please create one first.")
        return
    
    print(f"Found Exchange Account: ID={account.id}, Email={account.email}")
    
    # Update allowed accounts for the key
    api_key.allowed_accounts = [account.id]
    await api_key.save()
    print(f"Updated API Key permissions for Account ID: {account.id}")
    
    print("\n" + "="*50)
    print("SETUP COMPLETE")
    print("="*50)
    print(f"API_KEY={raw_key}")
    print(f"ACCOUNT_ID={account.id}")
    print("="*50)
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
