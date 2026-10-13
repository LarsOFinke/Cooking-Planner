"""HoverToggleButton widget behavior or control."""

from kivy.uix.togglebutton import ToggleButton
from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior
from cooking_planner.ui.widgets.RoundedControlBehavior import RoundedControlBehavior


class HoverToggleButton(RoundedControlBehavior, HoverColorBehavior, ToggleButton):
    pass
