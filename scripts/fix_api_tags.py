import asyncio
import os
import sys
from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.admin import Api

async def fix():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    print("Deleting all webhook-related APIs from DB...")
    deleted_count = await Api.filter(path__contains="webhook").delete()
    print(f"✅ Deleted {deleted_count} entries.")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(fix())
