"""HoverTextInput widget behavior or control."""

from kivy.uix.textinput import TextInput

from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior


class HoverTextInput(HoverColorBehavior, TextInput):
    hover_cursor = 'ibeam'
