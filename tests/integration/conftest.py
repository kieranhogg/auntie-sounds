from contextlib import AsyncExitStack

import pytest

from auntie_sounds.client import SoundsClient


@pytest.fixture
async def real_sounds_client():
    async with AsyncExitStack() as stack:
        client = SoundsClient()
        await stack.enter_async_context(client)
        yield client
