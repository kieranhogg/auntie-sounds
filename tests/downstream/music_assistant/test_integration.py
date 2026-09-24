import json

import pytest
import requests


@pytest.fixture(scope="session")
def ma_token(ma_server_url):
    # resp = requests.post(
    #     f"{ma_server_url}/setup", json={"username": "admin", "password": "password"}
    # )
    # if not resp.ok:
    #     pytest.fail("Setup request failed.")
    #
    # json_resp = json.loads(resp.content)
    # if not json_resp.get("success"):
    #     pytest.fail("Couldn't run setup.")
    # token = json_resp.get("token")
    # return token
    pass


@pytest.mark.downstream
class TestMusicAssistantIntegration:
    pass
