"""HoverToggleButton widget behavior or control."""

from kivy.uix.togglebutton import ToggleButton
from cooking_planner.ui.widgets.hover_color_behavior import HoverColorBehavior
from cooking_planner.ui.widgets.rounded_control_behavior import RoundedControlBehavior


class HoverToggleButton(RoundedControlBehavior, HoverColorBehavior, ToggleButton):
    pass
