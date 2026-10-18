"""HoverSpinner widget behavior or control."""

from kivy.uix.spinner import Spinner

from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior
from cooking_planner.ui.widgets.RoundedControlBehavior import RoundedControlBehavior


class HoverSpinner(RoundedControlBehavior, HoverColorBehavior, Spinner):
    pass
