from datetime import datetime
from enum import StrEnum, auto
from pathlib import Path

from aiohttp import request
from appdirs import AppDirs


class ImageType(StrEnum):
    """An enum for valid image types for recipes"""

    COLOUR = auto()
    COLOUR_DEFAULT = auto()
    BACKGROUND = auto()
    BLOCKS_COLOUR = auto()
    BLOCKS_COLOUR_BLACK = auto()
    BLOCKS_COLOUR_WHITE = auto()

def network_logo(
    logo_recipe: str,
    img_type: ImageType = ImageType.COLOUR,
    size: int = 450,
    file_extension: str = "png",
) -> str | None:
    """
    Formats a network logo based on the current recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}
    :param img_type An accepted image type
    :param size The required image size in pixels
    :param file_extension The expected file extension
    :return the full image URL as a string

    """
    if not logo_recipe:
        return None
    return logo_recipe.format(
        type=img_type, size=f"{size}x{size}", format=file_extension
    )


def image_from_recipe(
    image_recipe: str,
    size: int,
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


async def image_from_spotify(url: str) -> str | None:
    spotify_url = "https://open.spotify.com/oembed?url={url}"
    async with request("GET", spotify_url.format(url=url)) as resp:
        json_resp = await resp.json()
        if json_resp.get("thumbnail_url"):
            return json_resp.get("thumbnail_url")
    return None

def _get_data_dir() -> Path:
    dir = AppDirs(appname="auntie-sounds", version="1").user_data_dir
    Path(dir).mkdir(parents=True, exist_ok=True)
    return dir

def _date_with_ordinal(date_obj: datetime, format_string: str = "%A %-d$ %B") -> str:
    date_formatted = date_obj.strftime(format_string)
    if 4 <= date_obj.day <= 20 or 24 <= date_obj.day <= 30:
        ordinal = "th"
    else:
        ordinal = ["st", "nd", "rd"][date_obj.day % 10 - 1]

    return date_formatted.replace("$", ordinal)
