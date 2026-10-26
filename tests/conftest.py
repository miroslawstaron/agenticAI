import pytest

from agenticai.examples import seed
from agenticai.runtime import Manager
from agenticai.store import Store


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "data")
    seed(store)
    yield store
    store.close()


@pytest.fixture
async def manager(store):
    manager = Manager(store)
    yield manager
    await manager.close()
