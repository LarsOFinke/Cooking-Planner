"""HoverToggleButton widget behavior or control."""

from kivy.uix.togglebutton import ToggleButton
from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior
from cooking_planner.ui.widgets.RoundedControlBehavior import RoundedControlBehavior


class HoverToggleButton(RoundedControlBehavior, HoverColorBehavior, ToggleButton):
    def __init__(self, selected=False, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, 'activated'):
            self.activated = selected
        else:
            self.state = 'down' if selected else 'normal'

    @property
    def selected(self):
        return bool(self.activated) if hasattr(self, 'activated') else self.state == 'down'
