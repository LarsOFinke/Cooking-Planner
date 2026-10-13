"""HoverSurface widget behavior or control."""

from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from cooking_planner.ui.palette import PANEL
from cooking_planner.ui.widgets.HoverColorBehavior import HoverColorBehavior


class HoverSurface(HoverColorBehavior, BoxLayout):
    background_color = ListProperty(PANEL)
    hover_cursor = 'arrow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            tint = Color(*self.background_color)
            shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(background_color=lambda _, color: setattr(tint, 'rgba', color),
                  pos=lambda instance, _: setattr(shape, 'pos', instance.pos),
                  size=lambda instance, _: setattr(shape, 'size', instance.size))
