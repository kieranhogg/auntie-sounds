from dataclasses import fields
from typing import List

from .utils import network_logo
from .models import (
    Container,
    Menu,
    MenuItem,
    Network,
    PlayableItem,
    RadioShow,
    RecommendedMenuItem,
    Schedule,
    SearchResults,
    Segment,
    model_factory,
)

from collections import namedtuple


def parse_node(node):
    NestedObject = namedtuple("NestedObjects", ["source_key", "replacement_model"])
    nested_objects = [
        NestedObject("network", Network),
        NestedObject("container", Container),
        NestedObject("item", Container),
        NestedObject("programme", RadioShow),
        NestedObject("now", Network),
    ]
    ignored_objects = ["activities"]
    """
    Recursively parses a node. A node with a 'data' key is a container; otherwise, it's a playable item.
    """
    if isinstance(node, list):
        return [parse_node(item) for item in node]

    if "data" in node:
        container = model_factory(node)
        if not container:
            print("Warning, no container for node")
            return
        try:
            container.sub_items = parse_node(node["data"])
        except (ValueError, AttributeError):
            raise
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
        if (
            playable_item
            and hasattr(playable_item, "urn")
            and hasattr(playable_item, "pid")
            and (playable_item.urn is not None and playable_item.pid is None)
        ):
            playable_item.pid = playable_item.urn.split(":")[-1]
        if playable_item and getattr(playable_item, "network", None):
            playable_item.network.logo_url = network_logo(
                playable_item.network.logo_url
            )
        return playable_item


def parse_menu(json_data):
    menu = Menu(sub_items=[])
    if "data" in json_data:
        menu.sub_items = [
            parse_node(item) for item in json_data["data"] if item is not None
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
                    and menu_item.sub_items[0].recommendation is not None
                ):
                    data = {}
                    for field in fields(MenuItem):
                        data[field.name] = getattr(menu_item, field.name)

                    new_sub_menu.append(RecommendedMenuItem(**data))
                    continue
            new_sub_menu.append(menu_item)
    menu.sub_items = new_sub_menu
    return menu


def parse_schedule(json_data):
    schedule = parse_node(json_data["data"][0])
    return schedule


def parse_container(json_data) -> List[PlayableItem] | List[Segment] | None:
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


def parse_search(json_data):
    stations = []
    shows = []
    episodes = []
    for results_set in json_data["data"]:
        if results_set["id"] == "live_search":
            stations = parse_container(results_set)
        elif results_set["id"] == "container_search":
            shows = parse_container(results_set)
        elif results_set["id"] == "playable_search":
            episodes = parse_container(results_set)
    results = SearchResults(stations=stations, shows=shows, episodes=episodes)
    return results
