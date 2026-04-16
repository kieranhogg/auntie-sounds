from sounds.models import Menu, Podcast, PodcastEpisode, SearchResults
from sounds.parser import parse_menu, parse_node, parse_search


class TestParser:
    """Tests for parser functions"""

    # def test_parse_node_with_network(self, sample_network_data):
    #     """Test parsing a network node"""
    #     result = parse_node(sample_network_data)
    #     assert isinstance(result, Network)
    #     assert result.id == "bbc_radio_one"

    # def test_parse_node_with_list(self, sample_network_data):
    #     """Test parsing a list of nodes"""
    #     data = [sample_network_data, sample_network_data.copy()]
    #     data[1]["id"] = "bbc_radio_two"

    #     result = parse_node(data)
    #     assert isinstance(result, list)
    #     assert len(result) == 2
    #     assert all(isinstance(item, Network) for item in result)

    def test_parse_menu(self, sample_menu_data):
        """Test parsing menu data"""
        result = parse_menu(sample_menu_data)
        assert isinstance(result, Menu)
        assert result.sub_items is not None
        assert len(result.sub_items) == 10

    def test_parse_podcast_episode(self, sample_podcast_episode_data):
        """Test parsing podcast episode data"""
        result = parse_node(sample_podcast_episode_data)
        assert isinstance(result, PodcastEpisode)
        assert isinstance(result.container, Podcast)

    def test_parse_search_results(self):
        """Test parsing search results"""
        data = {
            "data": [
                {"id": "live_search", "data": []},
                {"id": "container_search", "data": []},
                {"id": "playable_search", "data": []},
            ]
        }
        result = parse_search(data)
        assert isinstance(result, SearchResults)
        assert hasattr(result, "stations")
        assert hasattr(result, "shows")
        assert hasattr(result, "episodes")
