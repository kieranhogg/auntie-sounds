import json
from logging import Logger

import pytest

from sounds.model_factory import ModelFactory
from sounds.models import Menu, Podcast, PodcastEpisode, RadioShow, SearchResults
from sounds.parser import Parser


class TestParser:
    """Tests for parser functions"""

    def test_parse_menu(self, sample_menu_data):
        """Test parsing menu data"""
        result = Parser().parse_menu(sample_menu_data)
        assert isinstance(result, Menu)
        assert result.sub_items is not None
        assert len(result.sub_items) == 10

    def test_parse_podcast_episode(self, sample_podcast_episode_data):
        """Test parsing podcast episode data"""
        result = Parser().parse_node(sample_podcast_episode_data)
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
        result = Parser().parse_search(data)
        assert isinstance(result, SearchResults)
        assert hasattr(result, "stations")
        assert hasattr(result, "shows")
        assert hasattr(result, "episodes")


class TestParserNestedObjects:
    def test_ignored_nested_objects(self: Logger):
        """Test that that embedded objects with keys in the ignore_objects list are removed."""
        parser = Parser()
        with open("tests/fixtures/api/PROGRAMME_FROM_PID_PLAYABLE.json") as json_file:
            json_data = json.loads(json_file.read())
            for key in parser.ignored_objects:
                assert key in json_data
                result = parser.parse_node(json_data)
                assert type(result) is RadioShow
                with pytest.raises(AttributeError):
                    getattr(result, key)

    def test_nested_objects(self: Logger):
        """Test that that embedded objects with keys in the nested_objects list are parsed as objects too.

        Currently:
            NestedObject("network", Network),
            NestedObject("container", Container),
        """
        data = {
            "type": "playable_item",
            "id": "p0p78bd4",
            "urn": "urn:bbc:radio:episode:m003169g",
            "network": {
                "id": "bbc_radio_four",
                "key": "radio4",
                "short_title": "Radio 4",
                "logo_url": "https://sounds.files.bbci.co.uk/3.12.0/networks/bbc_radio_four/{type}_{size}.{format}",
                "network_type": "master_brand",
                "services": [{"id": "id", "short_title": "title", "type": "type"}],
            },
            "container": {
                "type": "brand",
                "id": "p0h0q056",
                "urn": "urn:bbc:radio:brand:p0h0q056",
                "title": "The Traitors: Uncloaked",
                "synopses": {
                    "short": "Ed Gamble hosts the official Traitors visualised podcast with unseen bonus content.",
                    "medium": "Ed Gamble brings you exclusive unseen content from the castle as the banished and murdered players find out who the Traitors are.\n\nWatch on iPlayer here: https://bbc.in/48ilW3e",
                    "long": "Ed Gamble hosts the official visualised podcast for the ultimate game of trust and treachery. \n\nAlongside celebrity guests and fans, Ed brings you exclusive unseen content.\n\nYou can watch Uncloaked on iPlayer here: https://bbc.in/48ilW3e",
                },
                "activities": [],
            },
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        parser = Parser()
        result = parser.parse_node(data)
        for nested_object in ModelFactory.nested_objects:
            assert hasattr(result, nested_object.source_key) or hasattr(
                result.network, nested_object.source_key
            )  # For network->services
