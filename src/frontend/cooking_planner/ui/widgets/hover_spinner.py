"""HoverSpinner widget behavior or control."""

from kivy.uix.spinner import Spinner
from cooking_planner.ui.widgets.hover_color_behavior import HoverColorBehavior
from cooking_planner.ui.widgets.rounded_control_behavior import RoundedControlBehavior


class HoverSpinner(RoundedControlBehavior, HoverColorBehavior, Spinner):
    pass
