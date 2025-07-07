from src.sounds.constants import ImageType


def network_logo(
    logo_recipe: str,
    img_type: ImageType = ImageType.COLOUR,
    size: int = 450,
    img_format: str = "png",
) -> str:
    """
    Formats a network logo based on the current recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}
    :param img_type An accepted image type
    :param size The required image size in pixels

    :return the full image URL as a string

    """
    return logo_recipe.format(
        type=img_type.value, size=f"{size}x{size}", format=img_format
    )


def image_from_recipe(image_recipe, size) -> str:
    """
    Formats an image from a recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}

    :return the full image URL as a string
    """
    return image_recipe.format(recipe=size)
