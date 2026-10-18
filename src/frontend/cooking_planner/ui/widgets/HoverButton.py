"""HoverButton widget behavior or control."""

from kivy.uix.button import Button

from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior
from cooking_planner.ui.widgets.RoundedControlBehavior import RoundedControlBehavior


class HoverButton(RoundedControlBehavior, HoverColorBehavior, Button):
    pass
