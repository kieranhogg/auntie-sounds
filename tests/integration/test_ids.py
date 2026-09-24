from typing import ClassVar

from sounds.models import Network


class TestIDs:
    """Test the handling of a few edge-cases around network and service IDs

    The nuances of the internal models and the APIs mean there are a few areas
    where IDs change slightly depending on which endpoint is being used.

    BBC Radio Four is a network with an ID of bbc_radio_four.
    This network provides more than more service for Radio Four. We only care
    about the FM version, which has a service ID of bbc_radio_fourfm. So we
    need to take care when passing around objects and IDs in the library that
    we don't mix these up.

    Other examples are: bbc_radio_scotland_fm and bbc_radio_wales_fm
    """

    NETWORK_IDS_TO_CHECK: ClassVar = [
        "bbc_radio_four",
        "bbc_radio_scotland",
        "bbc_radio_wales",
    ]
    SERVICE_IDS_TO_CHECK: ClassVar = [
        "bbc_radio_fourfm",
        "bbc_radio_scotland_fm",
        "bbc_radio_wales_fm",
    ]

    async def test_ids_with_get_networks(self, sounds_client_with_mock_data):
        networks = await sounds_client_with_mock_data.stations._get_networks()
        network_ids = {network.id for network in networks}
        assert set(self.NETWORK_IDS_TO_CHECK).issubset(network_ids)
        assert set(self.SERVICE_IDS_TO_CHECK).isdisjoint(network_ids)

    async def test_id_from_network_object_is_correct_for_get_network(
        self, sounds_client_with_mock_data
    ):
        networks = await sounds_client_with_mock_data.stations.get_networks()
        radio_four = next(
            (network for network in networks if network.id == "bbc_radio_four"),
            None,
        )
        assert type(radio_four) is Network

        network = await sounds_client_with_mock_data.stations.get_network(radio_four.id)
        assert network.id == radio_four.id

    async def test_check_network_ids_against_methods(
        self, sounds_client_with_mock_data
    ):
        network_id = "bbc_radio_four"
        await sounds_client_with_mock_data.stations.get_station(network_id)
        menu = await sounds_client_with_mock_data.stations.get_radio_menu()
        ids = [item.id for item in menu.sub_items]
        assert network_id in ids
