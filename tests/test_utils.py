from dataclasses import dataclass

import pytest
from pytest import MarkDecorator

from sounds.utils import ImageType, image_from_recipe, network_logo

pytestmark: MarkDecorator = pytest.mark.anyio


class TestUtils:
    """Tests for utility functions."""

    def test_network_logo_formatting(self):
        """Test network logo URL formatting."""
        recipe = "https://example.com/{type}/{size}.{format}"
        result = network_logo(
            logo_recipe=recipe,
            img_type=ImageType.COLOUR,
            size=450,
            file_extension="png",
        )
        assert result == "https://example.com/colour/450x450.png"

    def test_network_logo_none_recipe(self):
        """Test network logo with None recipe."""
        result = network_logo("")
        assert result is None

    def test_image_from_recipe_square(self):
        """Test image recipe formatting for square images."""
        recipe = "https://example.com/{recipe}.{format}"
        result = image_from_recipe(recipe, size=640, file_extension="jpg")
        assert result == "https://example.com/640x640.jpg"

    def test_image_from_recipe_rectangle(self):
        """Test image recipe formatting for rectangular images."""
        recipe = "https://example.com/{recipe}.{format}"
        result = image_from_recipe(recipe, 640, height=480, file_extension="jpg")
        assert result == "https://example.com/640x480.jpg"

    def test_image_from_recipe_none(self):
        """Test image recipe with None input."""
        result = image_from_recipe("", 640)
        assert result is None

    def test_image_from_recipe_with_different_format(self):
        """Test image recipe with just a non-jpg format."""
        recipe = "https://example.com/{recipe}.{format}"
        result = image_from_recipe(recipe, 640, file_extension="png")
        assert result == "https://example.com/640x640.png"
