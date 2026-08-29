from collections import namedtuple
from collections.abc import Sequence
from dataclasses import fields
from logging import Logger

from sounds.exceptions import ParserError
from sounds.model_factory import ModelFactory
from sounds.models import (
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
)
from sounds.utils import network_logo

ParseResult = SoundsTypes | Sequence["ParseResult"] | None


class Parser:
    def __init__(self, logger: Logger):
        self.logger = logger

    def parse_node(
        self, node: dict, parent_network: dict | None = None
    ) -> SoundsTypes | list[SoundsTypes] | None:
        """
        Recursively parses a node. A node with a 'data' key is a container, otherwise,
        it's a playable item.
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
        model_factory = ModelFactory(logger=self.logger)
        if isinstance(node, list):
            # While we can have list of nodes and nodes within nodes,
            # we don't have lists of lists (or if we do we handle them in other functions)
            results = []
            for item in node:
                if item is not None:
                    parsed = self.parse_node(item, parent_network=parent_network)
                    if isinstance(parsed, list):
                        results.extend(parsed)
                    elif parsed is not None:
                        results.append(parsed)
            return results if results else None

        if "data" in node:
            node_network = node.get("network") or parent_network
            container = model_factory.parse_object(node, parent_network=node_network)
            if not container:
                return None

            if isinstance(container, (Container, CategoryItemContainer, Menu)):
                sub_items = self.parse_node(node["data"], parent_network=node_network)
                if isinstance(sub_items, list):
                    container.sub_items = sub_items

            return container

        else:
            playable_item = model_factory.parse_object(
                node, parent_network=parent_network
            )
            for nested_object in nested_objects:
                if nested_object.source_key not in ignored_objects and getattr(
                    playable_item, nested_object.source_key, None
                ):
                    source_dict = getattr(playable_item, nested_object.source_key)
                    out_object = model_factory.parse_object(
                        source_dict,
                        parent_network=getattr(playable_item, "network", None)
                        or parent_network,
                    )
                    if type(out_object) in [dict, None]:
                        msg = f"Failed to parse object: {source_dict}"
                        self.logger.error(msg)
                        raise ParserError(msg)
                    setattr(
                        playable_item,
                        nested_object.source_key,
                        out_object,
                    )

            # Post-processing
            if isinstance(playable_item, PlayableItem):
                if playable_item is not None and (
                    playable_item.urn and playable_item.pid
                ):
                    playable_item.pid = playable_item.urn.split(":")[-1]

                if playable_item.network and playable_item.network.logo_url:
                    playable_item.network.logo_url = network_logo(
                        playable_item.network.logo_url
                    )
            return playable_item

    def parse_menu(self, json_data: dict) -> Menu:
        menu = Menu(sub_items=[])

        if "data" not in json_data:
            return menu

        nodes = (
            self.parse_node(item) for item in json_data["data"] if item is not None
        )
        menu_items = [node for node in nodes if isinstance(node, MenuItem)]

        # Promote any menu item to a "recommended" variant if its first child is a recommendation
        menu.sub_items = [
            self._promote_if_recommended(item) for item in menu_items if item.sub_items
        ]
        return menu

    def _promote_if_recommended(self, menu_item: MenuItem) -> MenuItem:
        """Convert menu_item to RecommendedMenuItem if its first sub-item is a recommendation."""
        first_child = menu_item.sub_items[0]
        if getattr(first_child, "recommendation", None) is not None:
            data = {
                field.name: getattr(menu_item, field.name) for field in fields(MenuItem)
            }
            return RecommendedMenuItem(**data)
        return menu_item

    def parse_schedule(self, json_data: dict):
        schedule = self.parse_node(json_data["data"][0])
        return schedule

    def parse_container(
        self,
        json_data: dict,
    ) -> SoundsTypes | list[SoundsTypes] | None:
        if not json_data:
            return None
        if "data" in json_data:
            if (
                len(json_data["data"]) == 2
                and json_data["data"][0]["type"] == "inline_header_module"
                and json_data["data"][1]["type"] == "inline_display_module"
            ):
                item = json_data["data"][0]["data"]
                item["data"] = json_data["data"][1]["data"]
                container = self.parse_node(item)
            else:
                container = self.parse_node(json_data["data"])
        elif "results" in json_data:
            container = self.parse_node(json_data["results"])
        else:
            container = None
        return container

    def parse_search(self, json_data: dict) -> SearchResults:
        stations: list[LiveStation | StationSearchResult] = []
        shows: list[Podcast | RadioShow] = []
        episodes: list[PodcastEpisode | RadioShow | RadioClip] = []
        for results_set in json_data["data"]:
            if results_set["id"] == "live_search":
                station_results = self.parse_container(results_set)
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
                show_results = self.parse_container(results_set)
                if isinstance(show_results, list):
                    shows = [
                        show
                        for show in show_results
                        if isinstance(show, (Podcast, RadioShow))
                    ]
            elif results_set["id"] == "playable_search":
                episode_results = self.parse_container(results_set)
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
