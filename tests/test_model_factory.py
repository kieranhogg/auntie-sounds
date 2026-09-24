"""Tests for model_factory / parse_node, the core parsing and content-type
classification logic. This is where most of the BBC API's JSON shapes get
turned into typed models.
"""

import json

import pytest

from sounds.model_factory import ModelFactory
from sounds.models import (
    Collection,
    Category,
    Network,
    PlayableNetwork,
    Playlist,
    Podcast,
    PodcastEpisode,
    RadioClip,
    RadioShow,
    Segment,
    LiveStation,
    Station,
)
from sounds.parser import Parser

pytestmark = pytest.mark.anyio


class TestModelFactoryBasicTypes:
    """Basic factory usage."""

    def test_network_node(self):
        node = {
            "network_type": "master_brand",
            "id": "bbc_radio_one",
            "short_title": "Radio 1",
        }
        result = ModelFactory().parse_object(node)
        assert isinstance(result, Network)
        assert result.id == "bbc_radio_one"

    def test_list_of_nodes_via_parse_node(self):
        nodes = [
            {
                "type": "playable_item",
                "id": "m1",
                "urn": "urn:bbc:radio:episode:m1",
                "synopses": {"short": "", "medium": "", "long": ""},
                "titles": {
                    "primary": "",
                    "secondary": "",
                    "tertiary": "",
                    "entity_title": "",
                },
            },
            {
                "type": "playable_item",
                "id": "m2",
                "urn": "urn:bbc:radio:episode:m2",
                "titles": {
                    "primary": "",
                    "secondary": "",
                    "tertiary": "",
                    "entity_title": "",
                },
                "synopses": {},
            },
        ]
        result = Parser().parse_node(nodes)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, RadioShow) for item in result)

    def test_segment_item(self):
        node = {
            "type": "segment_item",
            "id": "seg1",
            "segment_type": "music",
            "titles": {
                "primary": "Song Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
            "image_url": None,
            "offset": {"start": 0},
            "uris": [],
        }
        result = Parser().parse_node(node)
        assert isinstance(result, Segment)
        assert result.id == "seg1"

    def test_collection_urn(self):
        node = {
            "type": "playable_item",
            "id": "coll1",
            "urn": "urn:bbc:radio:collection:coll1",
        }
        result = Parser().parse_node(node)
        assert isinstance(result, Collection)

    def test_category_urn(self):
        node = {
            "type": "playable_item",
            "id": "cat1",
            "urn": "urn:bbc:radio:category:cat1",
        }
        result = Parser().parse_node(node)
        assert isinstance(result, Category)


class TestEpisodeVsPodcastClassification:
    """An episode urn should become a RadioShow when there's no
    container, or when the container isn't a bbc_sounds_podcasts brand -
    otherwise it's a PodcastEpisode."""

    def test_episode_with_no_container_is_radio_show(self):
        node = {
            "type": "playable_item",
            "id": "m001",
            "urn": "urn:bbc:radio:episode:m001",
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert isinstance(result, RadioShow)

    def test_episode_in_podcast_brand_container_is_podcast_episode(self):
        node = {
            "type": "playable_item",
            "id": "m002",
            "urn": "urn:bbc:radio:episode:m002",
            "container": {"id": "brand", "type": "brand"},
            "network": {"id": "bbc_sounds_podcasts"},
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert isinstance(result, PodcastEpisode)

    def test_episode_in_non_podcast_brand_container_is_radio_show(self):
        node = {
            "type": "playable_item",
            "id": "m003",
            "urn": "urn:bbc:radio:episode:m003",
            "container": {"id": "brand", "type": "brand"},
            "network": {"id": "bbc_radio_one"},
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert isinstance(result, RadioShow)

    def test_bbc_news_podcast_is_podcast(self):
        """Test that a podcast associated with BBC News, and not a station is a Podcast not a RadioSeries."""
        with open("tests/fixtures/api/podcast_news.json") as node_file:
            node = json.loads(node_file.read())
            result = Parser().parse_node(node)
            assert isinstance(result.container, Podcast)


class TestClipVsPodcastClassification:
    def test_clip_with_no_brand_container_is_radio_clip(self):
        node = {
            "type": "playable_item",
            "id": "m010",
            "urn": "urn:bbc:radio:clip:m010",
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert isinstance(result, RadioClip)

    def test_clip_in_brand_container_is_podcast_episode(self):
        node = {
            "type": "playable_item",
            "id": "m011",
            "urn": "urn:bbc:radio:clip:m011",
            "container": {"id": "brand", "type": "brand"},
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert isinstance(result, PodcastEpisode)


class TestStationClassification:
    """LiveStation vs. plain Station depends entirely on whether
    'synopses' is present."""

    def test_station_with_synopses_is_live_station(self):
        node = {
            "type": "playable_item",
            "id": "radio1",
            "urn": "urn:bbc:radio:network:radio1",
            "synopses": {"short": "BBC Radio 1", "medium": "", "long": ""},
            "titles": {
                "primary": "Title",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
        }
        result = Parser().parse_node(node)
        assert type(result) is LiveStation

    def test_station_without_synopses_is_plain_station(self):
        node = {
            "type": "playable_item",
            "id": "radio1",
            "urn": "urn:bbc:radio:network:radio1",
        }
        result = Parser().parse_node(node)
        assert type(result) is Station

    def test_network_with_synopses_is_livestation(self):
        node = {
            "type": "playable_item",
            "id": "radio1",
            "urn": "urn:bbc:radio:network:radio1",
            "synopses": {"short": ""},
        }
        result = Parser().parse_node(node)
        assert type(result) is LiveStation


class TestPlaylists:
    def test_playlist_is_converted_correctly(self):
        node = {
            "type": "container_item",
            "uris": [
                {
                    "type": "latest",
                    "id": None,
                    "label": "Latest",
                    "uri": "/v2/curations/m002gj2t/members/playable?experience=domestic",
                }
            ],
            "id": "m002gj2t",
            "title": None,
            "description": None,
            "image_url": "https://ichef.bbci.co.uk/images/ic/1280x1280/p0p7mkxs.jpg",
            "synopses": {
                "short": "The world's greatest classical festival is coming to a close!",
                "medium": "Experience all the highlights from the world’s greatest classical music festival here. To listen on smart speaker just say, “ask BBC Sounds to play The Proms”",
                "long": "Experience all the highlights from the world’s greatest classical music festival here. To listen on smart speaker just say, “ask BBC Sounds to play The Proms”",
            },
            "titles": {
                "primary": "BBC Proms",
                "secondary": None,
                "tertiary": None,
                "entity_title": None,
            },
            "urn": "urn:bbc:radio:curation:m002gj2t",
            "network": None,
            "sub_items": [],
        }
        result = Parser().parse_node(node)
        assert isinstance(result, Playlist)


class TestProgrammes:
    def test_programme_podcast_episode(self):
        """Test the parser for programme endpoint data converts to podcast episode correctly"""
        with open("tests/fixtures/api/PROGRAMME_FROM_PID.json") as node_file:
            json_data = json.loads(node_file.read())
            original_object = json_data["data"][0]
            new_type, new_object = ModelFactory()._programme_episode(json_data)
            assert new_type is PodcastEpisode
            assert original_object == new_object

    def test_programme_radio_episode(self):
        """Test the parser for programme endpoint data converts to radio show correctly"""
        with open("tests/fixtures/api/PROGRAMME_FROM_PID.json") as node_file:
            json_data = json.loads(node_file.read())
            original_object = json_data["data"][0]

            # Remove the podcast type present in the test data
            del original_object["categories"][4]

            new_type, new_object = ModelFactory()._programme_episode(json_data)
            assert new_type is RadioShow
            assert original_object == new_object
