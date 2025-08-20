from dataclasses import fields

from .utils import network_logo
from .constants import ItemType
from .models import (
    Container,
    LiveStation,
    Menu,
    MenuItem,
    Network,
    PlayableItem,
    PromoItem,
    RadioShow,
    RecommendedMenuItem,
    SearchResults,
    # model_factory,
)
from .parsing import model_factory

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
    # elif "item" in node:
    #     container = model_factory(node)
    #     try:
    #         container.item = parse_node(node["item"])
    #     except ValueError:
    #         pass
    #     return container
    elif node.get("type") != ItemType.INLINE_DISPLAY_MODULE:
        playable_item = model_factory(node)
        for nested_object in nested_objects:
            try:
                if nested_object.source_key not in ignored_objects and getattr(
                    playable_item, nested_object.source_key, None
                ):
                    # original_dict = getattr(playable_item, nested_object.source_key)
                    # new_nested_object = model_factory(original_dict)
                    # setattr(
                    #     playable_item,
                    #     nested_object.source_key,
                    #     new_nested_object,
                    # )
                    # attrs_to_move = {
                    #     k: v
                    #     for k, v in original_dict.items()
                    #     if k not in ignored_objects
                    # }
                    source_dict = getattr(playable_item, nested_object.source_key)
                    out_object = model_factory(source_dict)
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
        # elif playable_item and getattr(playable_item, "station_image_url", None):
        #     playable_item.station_image_url = network_logo(
        #         playable_item.station_image_url
        #     )
        return playable_item
    else:
        # fallback for unknown types
        raise Exception(node)


def parse_menu(json_data):
    menu = Menu(sub_items=[])
    if "data" in json_data:
        parsed_items = parse_node(json_data["data"])
        menu.sub_items = [item for item in parsed_items if item is not None]

    # Post-process any menu items containing recommendations to make them recommendations
    # FIXME bad, bad, bad
    new_sub_menu = []
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
        # elif type(menu_item) is PromoItem:
        #     new_sub_menu.append(menu_item.sub_items[0].item)
        new_sub_menu.append(menu_item)
    menu.sub_items = new_sub_menu
    return menu


def parse_schedule(json_data):
    schedule = parse_node(json_data["data"][0])
    return schedule


def parse_container(json_data):
    container = parse_node(json_data["data"])
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
