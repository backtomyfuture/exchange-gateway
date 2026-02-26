import pytest

from app.core.crud import CRUDBase
from app.models.admin import User


@pytest.fixture
def user_crud():
    return CRUDBase(model=User)


@pytest.mark.asyncio
async def test_crud_get(user_crud):
    user = await User.filter(username="admin").first()
    result = await user_crud.get(id=user.id)
    assert result.username == "admin"


@pytest.mark.asyncio
async def test_crud_create(user_crud):
    obj = await user_crud.create(
        {
            "username": "crud_test_user",
            "email": "crud_test@test.com",
            "password": "hashed_pw",
            "is_active": True,
            "is_superuser": False,
        }
    )
    assert obj.id is not None
    assert obj.username == "crud_test_user"
    await obj.delete()


@pytest.mark.asyncio
async def test_crud_list(user_crud):
    total, items = await user_crud.list(page=1, page_size=10)
    assert total >= 1
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_crud_update(user_crud):
    user = await User.filter(username="admin").first()
    updated = await user_crud.update(id=user.id, obj_in={"alias": "Updated Admin"})
    assert updated.alias == "Updated Admin"
    await user_crud.update(id=user.id, obj_in={"alias": None})


@pytest.mark.asyncio
async def test_crud_remove(user_crud):
    obj = await user_crud.create(
        {
            "username": "to_delete",
            "email": "to_delete@test.com",
            "password": "hashed_pw",
            "is_active": True,
            "is_superuser": False,
        }
    )
    obj_id = obj.id
    await user_crud.remove(id=obj_id)
    from tortoise.exceptions import DoesNotExist

    with pytest.raises(DoesNotExist):
        await user_crud.get(id=obj_id)
