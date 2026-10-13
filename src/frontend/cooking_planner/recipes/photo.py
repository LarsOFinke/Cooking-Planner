"""Clickable recipe image used by the gallery."""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

from cooking_planner.ui.widgets.hover_image_behavior import HoverImageBehavior


class RecipePhoto(HoverImageBehavior, ButtonBehavior, Image):
    """An image that opens the recipe's gallery when clicked."""
