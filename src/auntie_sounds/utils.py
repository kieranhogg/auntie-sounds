from enum import StrEnum, auto
from pathlib import Path

from appdirs import AppDirs


class ImageType(StrEnum):
    """An enum for valid image types for recipes"""

    COLOUR = auto()
    COLOUR_DEFAULT = auto()
    BACKGROUND = auto()
    BLOCKS_COLOUR = auto()
    BLOCKS_COLOUR_BLACK = auto()
    BLOCKS_COLOUR_WHITE = auto()


def service_id_to_station_id(service_id):
    """bbc_radio_fourfm -> bbc_radio_four"""
    return "bbc_radio_four" if service_id == "bbc_radio_fourfm" else service_id


def station_id_to_service_id(station_id):
    """bbc_radio_four -> bbc_radio_fourfm"""
    return "bbc_radio_fourfm" if station_id == "bbc_radio_four" else station_id


def network_logo(
    logo_recipe: str,
    img_type: ImageType = ImageType.COLOUR,
    size: int = 450,
    network_id: str | None = None,
    file_extension: str = "png",
) -> str | None:
    """),
    Formats a network logo based on the current recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}
    :param img_type An accepted image type
    :param size The required image size in pixels
    :param network_id The network id
    :param file_extension The expected file extension
    :return the full image URL as a string

    """
    if not logo_recipe:
        return None
    if "network_id" in logo_recipe and network_id:
        return logo_recipe.format(
            type=img_type,
            size=f"{size}x{size}",
            format=file_extension,
            network_id=network_id,
        )
    else:
        return logo_recipe.format(
            type=img_type, size=f"{size}x{size}", format=file_extension
        )


def image_from_recipe(
    image_recipe: str,
    size: int = 400,
    height: int | None = None,
    file_extension: str | None = None,
    img_type: ImageType | None = None,
) -> str | None:
    """Formats an image from a recipe."""
    if not image_recipe:
        return image_recipe
    if height:
        img_size = f"{size}x{height}"
    else:
        img_size = f"{size}x{size}"

    if not file_extension:
        file_extension = "jpg"
    if "{format}" in image_recipe and file_extension:
        return image_recipe.format(format=file_extension, recipe=img_size)

    if "{type}" in image_recipe and img_type:
        return image_recipe.format(type=img_type, recipe=img_size)

    return image_recipe.format(recipe=img_size)


def _get_data_dir() -> Path:
    dir = Path(AppDirs(appname="auntie-sounds", version="1").user_data_dir)
    dir.mkdir(parents=True, exist_ok=True)
    return dir
