import os

# Force testing environment (Must be before any app imports)
os.environ["DEV_MODE"] = "true"
# Generate a valid base64 key (32 bytes)
import base64
os.environ["EXCHANGE_ENCRYPTION_KEY"] = base64.b64encode(os.urandom(32)).decode('utf-8')

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise
from app import app
from app.core.dependency import AuthControl
from app.core.init_app import init_superuser, init_menus, init_roles, init_apis
from app.models.admin import User
from app.settings import settings   

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    # Use ASGITransport to bypass lifespan if needed, or manage lifespan manually
    # Here we perform DB init manually, so we behave like the app is running
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "default",
            },
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()
    
    # Initialize basic data (bypass init_db which uses production config)
    # We need to mock settings.TORTOISE_ORM if we used init_db, but calling sub-functions is safer
    await init_superuser()
    await init_menus()
    # init_apis relies on app.routes, which is populated
    # But init_apis calls api_controller.refresh_api
    # api_controller needs to be imported
    await init_apis()
    await init_roles()
    
    yield
    await Tortoise.close_connections()

@pytest.fixture
async def superuser_token():
    from datetime import datetime, timedelta
    from app.utils.jwt_utils import create_access_token
    from app.schemas.login import JWTPayload
    from app.settings import settings
    
    user = await User.get(username="admin")
    
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = JWTPayload(
        user_id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
        exp=expire
    )
    return create_access_token(data=payload)

@pytest.fixture
async def normal_user_token():
    from datetime import datetime, timedelta
    from app.utils.jwt_utils import create_access_token
    from app.schemas.login import JWTPayload
    from app.settings import settings
    
    # Check if exists first
    user = await User.filter(username="normal_user").first()
    if not user:
        user = await User.create(
            username="normal_user",
            email="normal@test.com",
            password="password",
            is_active=True,
            is_superuser=False
        )
        # Assign normal user role
        from app.models.admin import Role
        role = await Role.get(name="普通用户")
        await user.roles.add(role)

    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = JWTPayload(
        user_id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
        exp=expire
    )
    return create_access_token(data=payload)

