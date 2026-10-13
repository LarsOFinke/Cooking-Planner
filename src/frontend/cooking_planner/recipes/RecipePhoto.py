"""Clickable recipe image used by the gallery."""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage

from cooking_planner.ui.widgets.HoverImageBehavior import HoverImageBehavior


class RecipePhoto(HoverImageBehavior, ButtonBehavior, AsyncImage):
    """An image that opens the recipe's gallery when clicked."""
