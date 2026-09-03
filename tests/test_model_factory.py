"""Tests for model_factory / parse_node, the core parsing and content-type
classification logic. This is where most of the BBC API's JSON shapes get
turned into typed models.
"""

import pytest

from sounds.models import (
    Category,
    Collection,
    LiveStation,
    Network,
    Playlist,
    PodcastEpisode,
    RadioClip,
    RadioShow,
    Segment,
    Station,
    model_factory,
)
from sounds.parser import parse_node

pytestmark = pytest.mark.anyio


class TestModelFactoryBasicTypes:
    """Basic factory usage."""

    def test_network_node(self):
        node = {
            "network_type": "master_brand",
            "id": "bbc_radio_one",
            "short_title": "Radio 1",
        }
        result = model_factory(node)
        assert isinstance(result, Network)
        assert result.id == "bbc_radio_one"

    def test_list_of_nodes_via_parse_node(self):
        nodes = [
            {
                "type": "playable_item",
                "id": "m1",
                "urn": "urn:bbc:radio:episode:m1",
            },
            {
                "type": "playable_item",
                "id": "m2",
                "urn": "urn:bbc:radio:episode:m2",
            },
        ]
        result = parse_node(nodes)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, RadioShow) for item in result)

    def test_segment_item(self):
        node = {
            "type": "segment_item",
            "id": "seg1",
            "segment_type": "music",
            "titles": {"primary": "Song Title"},
            "image_url": None,
            "offset": {"start": 0},
            "uris": [],
        }
        result = model_factory(node)
        assert isinstance(result, Segment)
        assert result.id == "seg1"

    def test_collection_urn(self):
        node = {
            "type": "playable_item",
            "id": "coll1",
            "urn": "urn:bbc:radio:collection:coll1",
        }
        result = model_factory(node)
        assert isinstance(result, Collection)

    def test_category_urn(self):
        node = {
            "type": "playable_item",
            "id": "cat1",
            "urn": "urn:bbc:radio:category:cat1",
        }
        result = model_factory(node)
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
        }
        result = model_factory(node)
        assert isinstance(result, RadioShow)

    def test_episode_in_podcast_brand_container_is_podcast_episode(self):
        node = {
            "type": "playable_item",
            "id": "m002",
            "urn": "urn:bbc:radio:episode:m002",
            "container": {"type": "brand"},
            "network": {"id": "bbc_sounds_podcasts"},
        }
        result = model_factory(node)
        assert isinstance(result, PodcastEpisode)

    def test_episode_in_non_podcast_brand_container_is_radio_show(self):
        node = {
            "type": "playable_item",
            "id": "m003",
            "urn": "urn:bbc:radio:episode:m003",
            "container": {"type": "brand"},
            "network": {"id": "bbc_radio_one"},
        }
        result = model_factory(node)
        assert isinstance(result, RadioShow)


class TestClipVsPodcastClassification:
    def test_clip_with_no_brand_container_is_radio_clip(self):
        node = {
            "type": "playable_item",
            "id": "m010",
            "urn": "urn:bbc:radio:clip:m010",
        }
        result = model_factory(node)
        assert isinstance(result, RadioClip)

    def test_clip_in_brand_container_is_podcast_episode(self):
        node = {
            "type": "playable_item",
            "id": "m011",
            "urn": "urn:bbc:radio:clip:m011",
            "container": {"type": "brand"},
        }
        result = model_factory(node)
        assert isinstance(result, PodcastEpisode)


class TestStationClassification:
    """LiveStation vs. plain Station depends entirely on whether
    'synopses' is present."""

    def test_station_with_synopses_is_live_station(self):
        node = {
            "type": "playable_item",
            "id": "radio1",
            "urn": "urn:bbc:radio:network:radio1",
            "synopses": {"short": "BBC Radio 1"},
        }
        result = model_factory(node)
        assert isinstance(result, LiveStation)

    def test_station_without_synopses_is_plain_station(self):
        node = {
            "type": "playable_item",
            "id": "radio1",
            "urn": "urn:bbc:radio:network:radio1",
        }
        result = model_factory(node)
        assert isinstance(result, Station)
        assert not isinstance(result, LiveStation)


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
            "titles": {"primary": "BBC Proms", "secondary": None, "tertiary": None},
            "urn": "urn:bbc:radio:curation:m002gj2t",
            "network": None,
            "sub_items": [],
        }
        result = model_factory(node)
        assert isinstance(result, Playlist)
