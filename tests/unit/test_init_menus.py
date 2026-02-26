import pytest

from app.core.init_app import init_menus
from app.models.admin import Menu


@pytest.mark.asyncio
async def test_init_menus_creates_all(init_test_db):
    count = await Menu.all().count()
    assert count > 0


@pytest.mark.asyncio
async def test_init_menus_idempotent(init_test_db):
    count_before = await Menu.all().count()
    await init_menus()
    count_after = await Menu.all().count()
    assert count_after == count_before
