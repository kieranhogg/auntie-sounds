import logging
from contextlib import AsyncExitStack

import pytest

from auntie_sounds.client import SoundsClient


@pytest.fixture
async def real_sounds_client():
    async with AsyncExitStack() as stack:
        client = SoundsClient()
        await stack.enter_async_context(client)
        yield client


@pytest.fixture(autouse=True)
def fail_on_api_shape_warnings(caplog):
    caplog.set_level(logging.WARNING, logger="auntie_sounds")
    yield
    warnings = [
        r
        for r in caplog.records
        if r.name.startswith("auntie_sounds") and r.levelno >= logging.WARNING
    ]
    if warnings:
        pytest.fail("\n".join(r.getMessage() for r in warnings))
