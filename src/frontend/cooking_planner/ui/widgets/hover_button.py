"""HoverButton widget behavior or control."""

from kivy.uix.button import Button
from cooking_planner.ui.widgets.hover_color_behavior import HoverColorBehavior
from cooking_planner.ui.widgets.rounded_control_behavior import RoundedControlBehavior


class HoverButton(RoundedControlBehavior, HoverColorBehavior, Button):
    pass
