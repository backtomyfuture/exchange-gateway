import asyncio
from tortoise import Tortoise, connections
# Use relative import if running as module, or fix path if running as script.
# Assuming running via: docker-compose exec app python3 scripts/prod_update.py
# We can use app.settings.config because /opt/app is in PYTHONPATH
from app.settings.config import settings
from app.models.admin import Menu, MenuType, Role, Api
from app.controllers.api import api_controller

async def main():
    print("Initializing DB connection...")
    await Tortoise.init(config=settings.TORTOISE_ORM)
    conn = connections.get("mysql")
    
    # Task 1: Unhide Department Menu
    print("Task 1: Unhiding Department Menu...")
    dept_menu = await Menu.filter(name="部门管理").first()
    if dept_menu:
        if dept_menu.is_hidden:
            dept_menu.is_hidden = False
            await dept_menu.save()
            print("Department menu unhidden.")
        else:
            print("Department menu is already visible.")
    else:
        print("Warning: Department menu not found. It might not be initialized yet.")
        # Optional: Initialize it if missing? init_app.py logic should handle creation if total absence.
        
    # Task 2: Apply Dept Schema Changes
    print("Task 2: Applying Dept Schema Changes...")
    try:
        print("Dropping index 'name'...")
        await conn.execute_script("ALTER TABLE `dept` DROP INDEX `name`;")
        print("Dropped index 'name'.")
    except Exception as e:
        print(f"Index 'name' drop skipped (might not exist): {e}")

    try:
        print("Adding unique index (parent_id, name)...")
        await conn.execute_script("ALTER TABLE `dept` ADD UNIQUE INDEX `dept_parent_id_name_unique` (`parent_id`, `name`);")
        print("Added scoped unique index.")
    except Exception as e:
        print(f"Index creation skipped (might exist): {e}")

    # Task 3: Fix Permissions (Assign Dept APIs)
    print("Task 3: Fixing Permissions...")
    # Refresh APIs to ensure new Dept APIs are in DB
    await api_controller.refresh_api()
    
    
    admin_role = await Role.filter(name="管理员").first()
    other_roles = await Role.filter(name__in=["邮箱用户", "飞书用户", "普通用户"]).all()
    
    dept_apis = await Api.filter(path__contains="/dept/")
    if not dept_apis:
        print("No Dept APIs found.")
    else:
        # 1. Admin gets ALL Dept APIs
        if admin_role:
            await admin_role.apis.add(*dept_apis)
            print(f"Assigned {len(dept_apis)} APIs to Admin role.")
            
            # Ensure Admin has ALL APIs (safety net)
            all_apis = await Api.all()
            await admin_role.apis.add(*all_apis)
            print("Ensured Admin has ALL APIs.")
            
        # 2. Other roles get READ-ONLY Dept APIs
        read_only_dept_apis = [api for api in dept_apis if api.method == "GET"]
        if other_roles:
            for role in other_roles:
                await role.apis.add(*read_only_dept_apis)
                print(f"Assigned {len(read_only_dept_apis)} READ APIs to role '{role.name}'.")

    print("Production update completed.")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
