from sounds.constants import ImageType
from sounds.utils import image_from_recipe, network_logo


class TestUtils:
    """Tests for utility functions"""

    def test_network_logo_formatting(self):
        """Test network logo URL formatting"""
        recipe = "https://example.com/{type}/{size}.{format}"
        result = network_logo(recipe, ImageType.COLOUR, 450, "png")
        assert result == "https://example.com/colour/450x450.png"

    def test_network_logo_none_recipe(self):
        """Test network logo with None recipe"""
        result = network_logo(None)
        assert result is None

    def test_image_from_recipe_square(self):
        """Test image recipe formatting for square images"""
        recipe = "https://example.com/{recipe}.{format}"
        result = image_from_recipe(recipe, size=640, format="jpg")
        assert result == "https://example.com/640x640.jpg"

    def test_image_from_recipe_rectangle(self):
        """Test image recipe formatting for rectangular images"""
        recipe = "https://example.com/{recipe}.{format}"
        result = image_from_recipe(recipe, 640, height=480, format="jpg")
        assert result == "https://example.com/640x480.jpg"

    def test_image_from_recipe_none(self):
        """Test image recipe with None input"""
        result = image_from_recipe(None, 640)
        assert result is None
