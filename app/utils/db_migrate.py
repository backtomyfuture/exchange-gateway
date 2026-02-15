import asyncio
from app.aerich_config import TORTOISE_ORM
from aerich import Command

async def run_migration():
    print("Starting database migration...")
    command = Command(tortoise_config=TORTOISE_ORM)
    await command.init()
    try:
        await command.upgrade()
        print("Migration upgrade successful!")
    except Exception as e:
        print(f"Migration upgrade result: {e}")
        # If 'No upgrade items found', it might raise exception or just print.
        # We catch to avoid crashing if it's just 'nothing to do'.

if __name__ == "__main__":
    asyncio.run(run_migration())
