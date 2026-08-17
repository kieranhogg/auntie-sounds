from sounds.models import Menu, Podcast, PodcastEpisode, SearchResults
from sounds.parser import Parser


class TestParser:
    """Tests for parser functions"""

    def test_parse_menu(self, logger, sample_menu_data):
        """Test parsing menu data"""
        result = Parser(logger).parse_menu(sample_menu_data)
        assert isinstance(result, Menu)
        assert result.sub_items is not None
        assert len(result.sub_items) == 10

    def test_parse_podcast_episode(self, logger, sample_podcast_episode_data):
        """Test parsing podcast episode data"""
        result = Parser(logger).parse_node(sample_podcast_episode_data)
        assert isinstance(result, PodcastEpisode)
        assert isinstance(result.container, Podcast)

    def test_parse_search_results(self, logger):
        """Test parsing search results"""
        data = {
            "data": [
                {"id": "live_search", "data": []},
                {"id": "container_search", "data": []},
                {"id": "playable_search", "data": []},
            ]
        }
        result = Parser(logger).parse_search(data)
        assert isinstance(result, SearchResults)
        assert hasattr(result, "stations")
        assert hasattr(result, "shows")
        assert hasattr(result, "episodes")
