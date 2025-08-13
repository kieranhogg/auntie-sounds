from .constants import ItemType
from .models import Container, Menu, Network, model_factory


from collections import namedtuple


def parse_node(node):
    NestedObject = namedtuple("NestedObjects", ["source_key", "replacement_model"])
    nested_objects = [
        NestedObject("network", Network),
        NestedObject("container", Container),
    ]
    ignored_objects = ["activities"]
    """
    Recursively parses a node. A node with a 'data' key is a container; otherwise, it's a playable item.
    """
    if isinstance(node, list):
        return [parse_node(item) for item in node]

    if "data" in node:
        container = model_factory(node)
        try:
            container.sub_items = parse_node(node["data"])
        except ValueError:
            pass
        return container
    elif node.get("type") != ItemType.MODULE:
        playable_item = model_factory(node)
        if type(playable_item) is str:
            raise Exception(playable_item)
        for nested_object in nested_objects:
            try:
                if getattr(playable_item, nested_object.source_key, None):
                    original_dict = getattr(playable_item, nested_object.source_key)
                    attrs_to_move = {
                        k: v
                        for k, v in original_dict.items()
                        if k not in ignored_objects
                    }
                    setattr(
                        playable_item,
                        nested_object.source_key,
                        nested_object.replacement_model(**attrs_to_move),
                    )
            except AttributeError:
                print(playable_item)
                raise
        return playable_item
    else:
        # fallback for unknown types
        raise Exception(node)


def parse_menu(json_data):
    menu = Menu(sub_items=[])
    if "data" in json_data:
        parsed_items = parse_node(json_data["data"])
        menu.sub_items = [item for item in parsed_items if item is not None]
    return menu
