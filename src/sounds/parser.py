from collections import namedtuple
from dataclasses import fields
from typing import List, Sequence, Union

from .models import (
    CategoryItemContainer,
    Container,
    LiveStation,
    Menu,
    MenuItem,
    Network,
    PlayableItem,
    Podcast,
    PodcastEpisode,
    RadioClip,
    RadioShow,
    RecommendedMenuItem,
    SearchResults,
    SoundsTypes,
    StationSearchResult,
    model_factory,
)
from .utils import network_logo

ParseResult = Union[SoundsTypes, Sequence["ParseResult"], None]


def parse_node(node) -> SoundsTypes | List[SoundsTypes] | None:
    """
    Recursively parses a node. A node with a 'data' key is a container; otherwise, it's a playable item.
    """

    NestedObject = namedtuple("NestedObject", ["source_key", "replacement_model"])
    nested_objects = [
        NestedObject("network", Network),
        NestedObject("container", Container),
        NestedObject("item", Container),
        NestedObject("programme", RadioShow),
        NestedObject("now", Network),
    ]
    ignored_objects = ["activities"]

    if isinstance(node, list):
        # While we can have list of nodes and nodes within nodes,
        # we don't have lists of lists (or if we do we handle them in other functions)
        results = []
        for item in node:
            if item is not None:
                parsed = parse_node(item)
                if isinstance(parsed, list):
                    results.extend(parsed)
                elif parsed is not None:
                    results.append(parsed)
        return results if results else None

    if "data" in node:
        container = model_factory(node)
        if not container:
            return None

        if isinstance(container, (Container, CategoryItemContainer, Menu)):
            sub_items = parse_node(node["data"])
            if isinstance(sub_items, list):
                container.sub_items = sub_items

        return container

    else:
        playable_item = model_factory(node)
        for nested_object in nested_objects:
            try:
                if nested_object.source_key not in ignored_objects and getattr(
                    playable_item, nested_object.source_key, None
                ):
                    source_dict = getattr(playable_item, nested_object.source_key)
                    out_object = model_factory(source_dict)
                    if type(out_object) in [dict, None]:
                        raise Exception("Failed to parse object: {source_dict}")
                    setattr(
                        playable_item,
                        nested_object.source_key,
                        out_object,
                    )
            except AttributeError:
                raise
        # Post-processing
        if isinstance(playable_item, PlayableItem):
            if playable_item is not None and (playable_item.urn and playable_item.pid):
                playable_item.pid = playable_item.urn.split(":")[-1]

            if playable_item.network and playable_item.network.logo_url:
                playable_item.network.logo_url = network_logo(
                    playable_item.network.logo_url
                )
        return playable_item


def parse_menu(json_data) -> Menu:
    menu = Menu(sub_items=[])
    if "data" in json_data:
        items = [parse_node(item) for item in json_data["data"] if item is not None]
        menu.sub_items = [
            sub_menu for sub_menu in items if isinstance(sub_menu, MenuItem)
        ]

    # Post-process any menu items containing recommendations to make them recommendations
    # FIXME bad, bad, bad
    new_sub_menu = []
    if menu and menu.sub_items:
        for menu_item in menu.sub_items:
            # If a menu item contains objects which are recommended, convert it to a recommended folder
            if (
                hasattr(menu_item, "sub_items")
                and menu_item.sub_items
                and len(menu_item.sub_items) > 0
            ):
                if (
                    menu_item.sub_items[0]
                    and hasattr(menu_item.sub_items[0], "recommendation")
                    and menu_item.sub_items[0].recommendation is not None
                ):
                    data = {}
                    for field in fields(MenuItem):
                        data[field.name] = getattr(menu_item, field.name)

                    new_sub_menu.append(RecommendedMenuItem(**data))
                    continue
            if isinstance(menu_item, RecommendedMenuItem):
                new_sub_menu.append(menu_item)
    menu.sub_items = new_sub_menu
    return menu


def parse_schedule(json_data):
    schedule = parse_node(json_data["data"][0])
    return schedule


def parse_container(
    json_data,
) -> SoundsTypes | List[SoundsTypes] | None:
    if "data" in json_data:
        if (
            len(json_data["data"]) == 2
            and json_data["data"][0]["type"] == "inline_header_module"
            and json_data["data"][1]["type"] == "inline_display_module"
        ):
            item = json_data["data"][0]["data"]
            item["data"] = json_data["data"][1]["data"]
            container = parse_node(item)
        else:
            container = parse_node(json_data["data"])
    elif "results" in json_data:
        container = parse_node(json_data["results"])
    else:
        container = None
    return container


def parse_search(json_data) -> SearchResults:
    stations: List[LiveStation | StationSearchResult] = []
    shows: List[Podcast | RadioShow] = []
    episodes: List[PodcastEpisode | RadioShow | RadioClip] = []
    for results_set in json_data["data"]:
        if results_set["id"] == "live_search":
            station_results = parse_container(results_set)
            if isinstance(station_results, list):
                stations = [
                    station
                    for station in station_results
                    if station
                    if isinstance(station, (LiveStation, StationSearchResult))
                ]
            else:
                stations = []
        elif results_set["id"] == "container_search":
            show_results = parse_container(results_set)
            if isinstance(show_results, list):
                shows = [
                    show
                    for show in show_results
                    if isinstance(show, (Podcast, RadioShow))
                ]
        elif results_set["id"] == "playable_search":
            episode_results = parse_container(results_set)
            if isinstance(episode_results, list):
                episodes = [
                    episode
                    for episode in episode_results
                    if isinstance(episode, (PodcastEpisode, RadioShow, RadioClip))
                ]
            else:
                episodes = []
    results = SearchResults(stations=stations, shows=shows, episodes=episodes)
    return results
