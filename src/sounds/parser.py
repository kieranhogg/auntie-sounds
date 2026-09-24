import logging
from dataclasses import fields

from sounds.model_factory import ModelFactory, parse_nested_objects
from sounds.models import (
    BasicContainer,
    CategoryItemContainer,
    Container,
    LiveStation,
    Menu,
    MenuItem,
    Podcast,
    PodcastEpisode,
    RadioClip,
    RadioShow,
    RecommendedMenuItem,
    SearchResults,
    SoundsTypes,
    StationSearchResult,
)

logger = logging.getLogger(__name__)


def _promote_if_recommended(menu_item: MenuItem) -> MenuItem:
    """Convert menu_item to RecommendedMenuItem if its first sub-item is a recommendation."""
    if not menu_item.sub_items:
        return menu_item
    first_child = menu_item.sub_items[0]
    if getattr(first_child, "recommendation", None) is not None:
        data = {
            field.name: getattr(menu_item, field.name) for field in fields(MenuItem)
        }
        return RecommendedMenuItem(**data)
    return menu_item


class Parser:
    def __init__(self):
        self.model_factory = ModelFactory()
        self.ignored_objects = ["activities"]

    def parse_node(
        self,
        node: dict | list,
        parent_network: dict | None = None,
        type_hint: SoundsTypes | None = None,
    ) -> SoundsTypes | list[SoundsTypes] | None:
        """
        Recursively parses a node. A node with a 'data' key is a container, otherwise,
        it's a playable item.
        """

        if isinstance(node, list):
            # While we can have list of nodes and nodes within nodes,
            # we don't have lists of lists (or if we do we handle them in other functions)
            results = []
            for item in node:
                if item is not None:
                    parsed = self.parse_node(
                        item, parent_network=parent_network, type_hint=type_hint
                    )
                    if isinstance(parsed, list):
                        results.extend(parsed)
                    elif parsed is not None:
                        results.append(parsed)
            return results if results else None

        if "data" in node:
            node_network = node.get("network") or parent_network
            container = self.model_factory.parse_object(
                node, parent_network=node_network, type_hint=type_hint
            )
            if not container:
                return None

            if isinstance(
                container, (BasicContainer, Container, CategoryItemContainer, Menu)
            ):
                sub_items = self.parse_node(
                    node["data"], parent_network=node_network, type_hint=type_hint
                )
                if isinstance(sub_items, list):
                    container.sub_items = sub_items

            return container

        else:
            playable_item = self.model_factory.parse_object(
                node, parent_network=parent_network, type_hint=type_hint
            )
            playable_item = parse_nested_objects(playable_item)
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
            _promote_if_recommended(item) for item in menu_items if item.sub_items
        ]
        return menu

    def parse_schedule(self, json_data: dict):
        schedule = self.parse_node(json_data["data"][0])
        return schedule

    def parse_container(
        self, json_data: dict, type_hint: SoundsTypes | None = None
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
                container = self.parse_node(item, type_hint=type_hint)
            else:
                container = self.parse_node(json_data["data"], type_hint=type_hint)
        elif "results" in json_data:
            container = self.parse_node(json_data["results"], type_hint=type_hint)
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
