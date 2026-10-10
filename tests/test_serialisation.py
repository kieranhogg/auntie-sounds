"""Models must survive a to_dict()/from_dict() round trip unchanged.

Downstream Music Assistant caches models this way, so a field type that doesn't match
the API shape, or a polymorphic field that comes back as a different class, breaks
cached lookups.
"""

import json
from collections.abc import Iterator

import pytest
from mashumaro import DataClassDictMixin

from auntie_sounds.models import MODEL_TAG, Container, LiveStation, Podcast, RadioShow
from auntie_sounds.parser import Parser

from .conftest import FIXTURES_FOLDER

# Category dicts only ever appear nested (as ItemCategory or raw dicts); fed to
# the factory on their own they hit the "has a key -> Network" fallback.
_NOT_TOP_LEVEL = {"genre", "format", "category_summary"}


def _nodes(obj) -> Iterator[dict]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _nodes(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _nodes(value)


def _try_parse(node: dict):
    try:
        return Parser().parse_node(node)
    except AttributeError:
        # Not every nested dict is a parseable node
        return None


def _parsed_models(data) -> Iterator[DataClassDictMixin]:
    for node in _nodes(data):
        if "type" not in node or node["type"] in _NOT_TOP_LEVEL:
            continue
        obj = _try_parse(node)
        if isinstance(obj, DataClassDictMixin):
            yield obj


_FIXTURES = sorted(
    p for p in FIXTURES_FOLDER.glob("*.json") if p.read_text(errors="ignore").strip()
)


@pytest.mark.parametrize("path", _FIXTURES, ids=lambda p: p.stem)
def test_fixture_models_round_trip(path):
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        pytest.skip("not JSON")

    models = list(_parsed_models(data))
    if not models:
        pytest.skip("no models parsed")

    for obj in models:
        restored = type(obj).from_dict(obj.to_dict())
        # dataclass __eq__ requires identical classes, so this also catches
        # nested subclasses collapsing to a sibling/base class.
        assert restored == obj, f"{type(obj).__name__} {getattr(obj, 'id', '')}"


def test_polymorphic_fields_keep_concrete_type():
    show = RadioShow(id="p1", container=Podcast(id="c1"))
    parent = Container(id="m", sub_items=[show, Podcast(id="c2")])

    data = parent.to_dict()
    assert data[MODEL_TAG] == "Container"
    assert data["sub_items"][0][MODEL_TAG] == "RadioShow"

    restored = Container.from_dict(data)
    assert type(restored.sub_items[0]) is RadioShow
    assert type(restored.sub_items[0].container) is Podcast
    assert type(restored.sub_items[1]) is Podcast


def test_live_station_empty_uris_round_trip():
    station = LiveStation(id="bbc_radio_fourfm", uris=[])
    assert LiveStation.from_dict(station.to_dict()) == station
