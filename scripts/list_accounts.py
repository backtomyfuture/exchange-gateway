import asyncio
import os
import sys

from tortoise import Tortoise

sys.path.append(os.getcwd())
# Set DEV_MODE
os.environ.setdefault("DEV_MODE", "true")
from app.models.exchange import ExchangeAccount
from app.settings import settings


async def list_accounts():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    accounts = await ExchangeAccount.all()
    print(f"Found {len(accounts)} accounts:")
    for acc in accounts:
        print(f"ID: {acc.id}, Email: {acc.email}, Server: {acc.server}")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(list_accounts())
