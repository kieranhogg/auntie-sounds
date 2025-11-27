from .constants import ImageType


def network_logo(
    logo_recipe: str,
    img_type: ImageType = ImageType.COLOUR,
    size: int = 450,
    img_format: str = "png",
) -> str | None:
    """
    Formats a network logo based on the current recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}
    :param img_type An accepted image type
    :param size The required image size in pixels

    :return the full image URL as a string

    """
    if not logo_recipe:
        return None
    return logo_recipe.format(
        type=img_type.value, size=f"{size}x{size}", format=img_format
    )


def image_from_recipe(
    image_recipe: str,
    size: int,
    height: int | None = None,
    format="jpg",
    img_type: ImageType | None = None,
) -> str | None:
    """
    Formats an image from a recipe

    :param logo_recipe e.g. http://example.com/{type}/{size}_{size}.{format}

    :return the full image URL as a string
    """
    if not image_recipe:
        return image_recipe
    if height:
        img_size = f"{size}x{height}"
    else:
        img_size = f"{size}x{size}"

    if "format" in image_recipe and format:
        image_recipe = image_recipe.format(format=format, recipe=img_size)
    elif "type" in image_recipe and img_type:
        image_recipe = image_recipe.format(type=img_type, recipe=img_size)
    else:
        image_recipe = image_recipe.format(recipe=img_size)

    return image_recipe
