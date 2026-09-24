

class TestNetworks:
    async def test_all_networks_have_a_service(self, sounds_client_with_mock_data):
        networks = await sounds_client_with_mock_data.stations.get_networks()

        for network in networks:
            assert network.service is not None
