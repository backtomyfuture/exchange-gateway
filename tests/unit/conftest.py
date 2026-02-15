
import pytest

# Override init_test_db to do nothing
@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    yield
