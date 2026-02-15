import asyncio
import os
import sys
from tortoise import Tortoise

sys.path.append(os.getcwd())
os.environ.setdefault("DEV_MODE", "true")

from app.settings import settings
from app.models.admin import User, Role, Menu

async def check():
    await Tortoise.init(config=settings.TORTOISE_ORM)
    
    user = await User.filter(username="q-fu1").first()
    if not user:
        print("❌ User 'q-fu1' not found!")
        return

    print(f"--- User: {user.username} (ID: {user.id}) ---")
    roles = await user.roles.all()
    print(f"Roles: {[r.name for r in roles]}")
    
    for r in roles:
        menus = await r.menus.all()
        print(f"Role '{r.name}' Menus: {[m.name for m in menus]}")
        # Also check if parent menus are implicitly included or need to be explicit
        for m in menus:
            if m.parent_id != 0:
                parent = await Menu.get(id=m.parent_id)
                print(f"  -> Sub-menu: {m.name} (Parent: {parent.name} ID: {parent.id})")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(check())
