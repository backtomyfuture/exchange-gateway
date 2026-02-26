import asyncio
import os
import sys

from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.models.admin import Menu
from app.settings import settings


async def inspect():
    await Tortoise.init(config=settings.TORTOISE_ORM)

    print("--- Menus in DB ---")
    menus = await Menu.all().order_by("parent_id", "order")
    for m in menus:
        print(
            f"ID: {m.id} | Parent: {m.parent_id} | Name: {m.name} | Path: {m.path} | Component: {m.component} | Type: {m.menu_type} | Order: {m.order} | Hidden: {m.is_hidden}"
        )

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(inspect())
