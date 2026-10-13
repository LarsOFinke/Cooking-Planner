"""HoverTextInput widget behavior or control."""

from kivy.uix.textinput import TextInput
from cooking_planner.ui.widgets.hover_color_behavior import HoverColorBehavior


class HoverTextInput(HoverColorBehavior, TextInput):
    hover_cursor = 'ibeam'
