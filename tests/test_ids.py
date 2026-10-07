"""Tests for how models identify themselves.

We expose item_id as an external ID for downstream providers. It therefore must be:
* stable: the same object gets the same ID, whichever endpoint it came from
* unique: different things give different values
* enough to look the item up again with no other context

The rules being tested, per kind of object:

* Episode, clip, show: episode/clip pid (urn tail)
* Scheduled item: episode pid (urn tail)
* Container: pid (urn tail)
* Segment: record id (urn tail)
* Station: service id, e.g. bbc_radio_fourfm
* Network: network id, e.g. bbc_radio_four
"""

import inspect
import logging
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta

import pytest

from sounds import models
from sounds.models import (
    Audiobook,
    AudiobookEpisode,
    BasicContainer,
    Category,
    Collection,
    Container,
    DisplayItem,
    ImageMixin,
    LiveProgramme,
    LiveStation,
    MenuItem,
    Network,
    PlayableItem,
    PlayableNetwork,
    Playlist,
    Podcast,
    PodcastEpisode,
    PromoItem,
    RadioClip,
    RadioSeries,
    RadioShow,
    RecommendedMenuItem,
    Schedule,
    ScheduleItem,
    Season,
    Segment,
    Station,
    StationSearchResult,
    pid_from_urn,
)

LOGGER = logging.getLogger(__name__)

EPISODE_PID = "m002abcd"
EPISODE_URN = f"urn:bbc:radio:episode:{EPISODE_PID}"
CLIP_PID = "p0clip01"
VPID = "p0vers01"
BROADCAST_PID = "m00bcast"
BRAND_PID = "b006s6p6"
BRAND_URN = f"urn:bbc:radio:brand:{BRAND_PID}"


def build(cls, **kwargs):
    """Construct then post-process, as the parser does."""
    obj = cls(**kwargs)
    obj.post_processing(LOGGER)
    return obj


def concrete_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from concrete_subclasses(sub)


###### Helper ###################################################################
@pytest.mark.parametrize(
    ("urn", "expected"),
    [
        (None, None),
        ("", None),
        (EPISODE_URN, EPISODE_PID),
        ("urn:bbc:radio:network:bbc_radio_four", "bbc_radio_four"),
        ("urn:bbc:radio:segment:music:abc123", "abc123"),
        ("bare", "bare"),
    ],
)
def test_pid_from_urn(urn, expected):
    assert pid_from_urn(urn) == expected


###### On-demand playables: id is the version, urn is the episode ################
# (class, extra kwargs needed to construct it)
PLAYABLES = [
    pytest.param(PlayableItem, {}, id="PlayableItem"),
    pytest.param(PodcastEpisode, {}, id="PodcastEpisode"),
    pytest.param(RadioShow, {}, id="RadioShow"),
    pytest.param(LiveProgramme, {}, id="LiveProgramme"),
    pytest.param(
        AudiobookEpisode,
        {"container": Container(id=BRAND_PID, urn=BRAND_URN)},
        id="AudiobookEpisode",
    ),
]


@pytest.mark.parametrize(("cls", "extra"), PLAYABLES)
def test_playable_item_id_is_episode_pid_not_vpid(cls, extra):
    """On the playable endpoints id is the version pid, urn is the episode."""
    item = build(cls, id=VPID, urn=EPISODE_URN, **extra)

    assert item.item_id == EPISODE_PID
    assert item.pid == EPISODE_PID
    assert item.version_pid == VPID


def test_clip_item_id_is_clip_pid():
    clip = build(RadioClip, id=VPID, urn=f"urn:bbc:radio:clip:{CLIP_PID}")

    assert clip.item_id == CLIP_PID
    assert clip.version_pid == VPID


@pytest.mark.parametrize(("cls", "extra"), PLAYABLES)
def test_same_episode_has_same_item_id_whatever_the_class(cls, extra):
    """MA must see one episode as one item, however it was fetched."""
    from_playable = build(cls, id=VPID, urn=EPISODE_URN, **extra)
    from_schedule = build(ScheduleItem, id=BROADCAST_PID, urn=EPISODE_URN)

    assert from_playable.item_id == from_schedule.item_id


@pytest.mark.parametrize("cls", [PodcastEpisode, RadioShow, PlayableItem])
def test_programme_shape_without_urn(cls):
    """Programme responses have no urn: id is the pid, availability.id the vpid."""
    item = build(
        cls,
        id=EPISODE_PID,
        availability={"id": VPID, "duration": 1590},
        images=[{"type": "standard", "url": "https://example/{recipe}.jpg"}],
    )

    assert item.item_id == EPISODE_PID
    assert item.pid == EPISODE_PID
    assert item.version_pid == VPID


def test_without_urn_or_availability_id_is_not_guessed_to_be_a_pid():
    """With nothing to say id isn't the vpid, don't claim it's a pid."""
    item = build(RadioShow, id="mystery1")

    assert item.pid is None
    assert item.version_pid is None


def test_availability_id_beats_the_id_guess_for_version_pid():
    item = build(RadioShow, id=VPID, urn=EPISODE_URN, availability={"id": "p0other1"})

    assert item.version_pid == "p0other1"


def test_explicit_version_pid_is_kept():
    item = build(RadioShow, id=VPID, urn=EPISODE_URN, version_pid="p0given1")

    assert item.version_pid == "p0given1"


###### Scheduled items: id is the broadcast, urn is the episode ##################
def test_schedule_item_can_be_constructed():
    """pid is a real field, so a read-only property must not shadow it."""
    ScheduleItem(id=BROADCAST_PID, urn=EPISODE_URN)


def test_schedule_item_ids():
    item = build(ScheduleItem, id=BROADCAST_PID, urn=EPISODE_URN)

    assert item.broadcast_pid == BROADCAST_PID
    assert item.pid == EPISODE_PID
    assert item.item_id == EPISODE_PID


def test_schedule_item_never_mistakes_broadcast_pid_for_version_pid():
    item = build(ScheduleItem, id=BROADCAST_PID, urn=EPISODE_URN)

    assert item.version_pid is None
    assert item.vpid is None


def test_schedule_item_vpid_is_version_pid():
    item = build(ScheduleItem, id=BROADCAST_PID, urn=EPISODE_URN, version_pid=VPID)

    assert item.version_pid == VPID
    assert item.vpid == VPID


def test_schedule_item_runs_playable_item_post_processing():
    """ImageMixin must not sit ahead of PlayableItem and swallow its setup."""
    start = datetime(2026, 1, 1, 6, tzinfo=UTC)
    item = build(
        ScheduleItem,
        id=BROADCAST_PID,
        urn=EPISODE_URN,
        start=start.isoformat(),
        end=(start + timedelta(hours=1)).isoformat(),
        availability={"id": VPID, "duration": 3600},
    )

    assert item.start == start
    assert item.version_pid == VPID
    assert item.pid == EPISODE_PID


def test_schedule_item_processes_image_once(monkeypatch):
    calls = []

    def fake_recipe(url, size=1280):
        calls.append(url)
        return url

    monkeypatch.setattr(models, "image_from_recipe", fake_recipe)
    build(
        ScheduleItem,
        id=BROADCAST_PID,
        urn=EPISODE_URN,
        image_url="https://example/{recipe}.jpg",
    )

    assert len(calls) == 1


def test_get_current_item_finds_the_live_item():
    now = datetime.now(UTC)
    live = build(
        ScheduleItem,
        id="m00live1",
        urn="urn:bbc:radio:episode:m00live0",
        start=(now - timedelta(minutes=30)).isoformat(),
        end=(now + timedelta(minutes=30)).isoformat(),
    )
    later = build(
        ScheduleItem,
        id="m00later",
        urn="urn:bbc:radio:episode:m00late0",
        start=(now + timedelta(hours=1)).isoformat(),
        end=(now + timedelta(hours=2)).isoformat(),
    )
    schedule = Schedule(id="bbc_radio_four", sub_items=[later, live])

    assert schedule.get_current_item() is live


def test_schedule_item_survives_a_serialisation_round_trip():
    item = build(ScheduleItem, id=BROADCAST_PID, urn=EPISODE_URN, version_pid=VPID)
    schedule = Schedule(id="bbc_radio_four", sub_items=[item])

    restored = Schedule.from_dict(schedule.to_dict())

    (restored_item,) = restored.sub_items
    assert type(restored_item) is ScheduleItem
    assert restored_item.item_id == EPISODE_PID
    assert restored_item.broadcast_pid == BROADCAST_PID
    assert restored_item.version_pid == VPID


###### Containers: id and urn tail agree, pid is the fallback ####################
def promo():
    return PlayableItem(id=VPID, urn=EPISODE_URN)


CONTAINERS = [
    pytest.param(Container, {}, id="Container"),
    pytest.param(Podcast, {}, id="Podcast"),
    pytest.param(Audiobook, {}, id="Audiobook"),
    pytest.param(RadioSeries, {}, id="RadioSeries"),
    pytest.param(Collection, {}, id="Collection"),
    pytest.param(Category, {}, id="Category"),
    pytest.param(Playlist, {}, id="Playlist"),
    pytest.param(MenuItem, {}, id="MenuItem"),
    pytest.param(RecommendedMenuItem, {}, id="RecommendedMenuItem"),
    pytest.param(Season, {}, id="Season"),
    pytest.param(DisplayItem, {}, id="DisplayItem"),
    pytest.param(PromoItem, {"item": promo()}, id="PromoItem"),
]


@pytest.mark.parametrize(("cls", "extra"), CONTAINERS)
def test_container_item_id_is_urn_tail(cls, extra):
    item = build(cls, id=BRAND_PID, urn=BRAND_URN, **extra)

    assert item.item_id == BRAND_PID


@pytest.mark.parametrize(("cls", "extra"), CONTAINERS)
def test_container_item_id_falls_back_to_pid_then_id(cls, extra):
    with_pid = build(cls, pid=BRAND_PID, **extra)
    with_id = build(cls, id="some_id", **extra)

    assert with_pid.item_id == BRAND_PID
    assert with_id.item_id == "some_id"


def test_podcast_from_pid_endpoint_has_only_a_pid():
    """/podcasts/{pid} has pid but no id or urn."""
    assert build(Podcast, pid=BRAND_PID).item_id == BRAND_PID


def test_single_item_promo_uses_its_own_uuid():
    uuid = "d3157051-ac4c-43bc-9977-dc5b77cf7453"
    item = build(
        PromoItem,
        id=uuid,
        urn=f"urn:bbc:radio:single_item_promo:{uuid}",
        item=promo(),
    )

    assert item.item_id == uuid


###### Segments ##################################################################
def test_segment_item_id_is_the_record_not_the_occurrence():
    """A track is the same track every time it is played."""
    segment = Segment(
        id="seg0001",
        segment_type="music",
        uris=[],
        urn="urn:bbc:radio:segment:music:rec0001",
        image_url=None,
        offset=None,
    )

    assert segment.item_id == "rec0001"
    assert segment.record_id == "rec0001"


def test_segment_without_urn_falls_back_to_id():
    segment = Segment(
        id="seg0001", segment_type="music", uris=[], image_url=None, offset=None
    )

    assert segment.item_id == "seg0001"
    assert segment.record_id is None


###### Stations and networks #####################################################
# Radio 4 has network id bbc_radio_four but service id bbc_radio_fourfm.
# Radio Scotland has one network and two services (FM and MW), so the
# network id can't tell them apart: only the service id is unique per stream.
@pytest.mark.parametrize(
    ("service_id", "network_urn"),
    [
        ("bbc_radio_fourfm", "urn:bbc:radio:network:bbc_radio_four"),
        ("bbc_radio_scotland_fm", "urn:bbc:radio:network:bbc_radio_scotland"),
        ("bbc_radio_scotland_mw", "urn:bbc:radio:network:bbc_radio_scotland"),
        ("bbc_6music", "urn:bbc:radio:network:bbc_6music"),
    ],
)
def test_station_item_id_is_the_service_id(service_id, network_urn):
    live = build(LiveStation, id=service_id, urn=network_urn)
    station = build(Station, id=service_id, urn=network_urn)

    assert live.item_id == service_id
    assert station.item_id == service_id


def test_playable_network_item_id_is_the_service_id_once_flattened():
    flattened = build(
        PlayableNetwork,
        id="bbc_radio_fourfm",
        urn="urn:bbc:radio:network:bbc_radio_four",
        network=Network(id="bbc_radio_four"),
    )

    assert flattened.id == "bbc_radio_four"
    assert flattened.service_id == "bbc_radio_fourfm"
    assert flattened.item_id == "bbc_radio_fourfm"


def test_station_search_result_item_id_is_the_service_id():
    result = StationSearchResult(
        id="not-the-station",
        type="station",
        urn="urn:bbc:radio:network:bbc_radio_four",
        service_id="bbc_radio_fourfm",
        episode_image_url=None,
        station_image_url=None,
        station_name="Radio 4",
        title="Today",
        short_synopsis="",
        progress=None,
        duration=None,
    )

    assert result.item_id == "bbc_radio_fourfm"


def test_one_station_has_one_item_id_across_models():
    ids = {
        build(
            LiveStation,
            id="bbc_radio_fourfm",
            urn="urn:bbc:radio:network:bbc_radio_four",
        ).item_id,
        build(Station, id="bbc_radio_fourfm").item_id,
        build(
            PlayableNetwork,
            id="bbc_radio_fourfm",
            urn="urn:bbc:radio:network:bbc_radio_four",
            network=Network(id="bbc_radio_four"),
        ).item_id,
    }

    assert ids == {"bbc_radio_fourfm"}


def test_network_item_id_is_the_network_id():
    assert Network(id="bbc_radio_four").item_id == "bbc_radio_four"


def test_station_live_version_pid_is_the_service_id():
    """The media selector plays a live station by its service id."""
    live = build(
        LiveStation,
        id="bbc_radio_fourfm",
        urn="urn:bbc:radio:network:bbc_radio_four",
    )

    assert live.version_pid == "bbc_radio_fourfm"


@pytest.mark.parametrize(
    ("cls", "service_id", "network_urn"),
    [
        (
            LiveStation,
            "bbc_radio_scotland_fm",
            "urn:bbc:radio:network:bbc_radio_scotland",
        ),
        (Station, "bbc_radio_scotland_fm", None),
        (LiveStation, "bbc_radio_fourfm", "urn:bbc:radio:network:bbc_radio_four"),
    ],
)
def test_station_description_is_looked_up_by_service_id(cls, service_id, network_urn):
    """Looking up by pid found nothing for Station, and only network ids for LiveStation."""
    station = build(cls, id=service_id, urn=network_urn)

    assert station.description


###### Things that must not have an item_id ######################################
def test_basic_container_is_not_identifiable():
    assert not hasattr(BasicContainer(), "item_id")


###### Structural guards #########################################################
ALL_MODELS = [
    cls
    for cls in vars(models).values()
    if inspect.isclass(cls) and is_dataclass(cls) and cls.__module__ == models.__name__
]


@pytest.mark.parametrize("cls", ALL_MODELS, ids=lambda c: c.__name__)
def test_no_property_shadows_a_dataclass_field(cls):
    """A read-only property over a field breaks the generated __init__."""
    shadowed = [
        f.name
        for f in fields(cls)
        if isinstance(inspect.getattr_static(cls, f.name, None), property)
    ]

    assert not shadowed


PLAYABLE_SUBCLASSES = [PlayableItem, *concrete_subclasses(PlayableItem)]


@pytest.mark.parametrize("cls", PLAYABLE_SUBCLASSES, ids=lambda c: c.__name__)
def test_playable_item_comes_before_image_mixin_in_the_mro(cls):
    """Otherwise ImageMixin.post_processing hides PlayableItem's."""
    mro = cls.__mro__

    if ImageMixin in mro:
        assert mro.index(PlayableItem) < mro.index(ImageMixin)


@pytest.mark.parametrize("cls", PLAYABLE_SUBCLASSES, ids=lambda c: c.__name__)
def test_is_live_is_a_property_on_every_playable_item(cls):
    """A TimedContent method must not be hidden behind the property."""
    assert isinstance(inspect.getattr_static(cls, "is_live"), property)
    assert not any(k.__name__ == "TimedContent" for k in cls.__mro__)
