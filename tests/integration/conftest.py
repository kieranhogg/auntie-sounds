import pytest

from sounds.client import SoundsClient


@pytest.fixture
async def real_sounds_client():
    client = SoundsClient()
    yield client
    await client.close()
