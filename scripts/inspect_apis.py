import asyncio
import os
import sys

from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.models.admin import Api
from app.settings import settings


async def inspect():
    await Tortoise.init(config=settings.TORTOISE_ORM)

    print("--- Detailed Webhook APIs in DB ---")
    apis = await Api.filter(path__contains="webhook").all()
    for api in apis:
        print(
            f"ID: {api.id} | Method: {api.method} | Path: {api.path} | Tag: {repr(api.tags)} | Summary: {repr(api.summary)}"
        )

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(inspect())
