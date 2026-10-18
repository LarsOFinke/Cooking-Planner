"""HoverSpinnerOption widget behavior or control."""

from kivy.uix.spinner import SpinnerOption

from cooking_planner.ui.palette import PANEL_LIGHT, WHITE
from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior
from cooking_planner.ui.widgets.RoundedControlBehavior import RoundedControlBehavior


class HoverSpinnerOption(RoundedControlBehavior, HoverColorBehavior, SpinnerOption):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('background_color', PANEL_LIGHT)
        kwargs.setdefault('color', WHITE)
        super().__init__(**kwargs)
