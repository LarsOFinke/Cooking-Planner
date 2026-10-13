"""RoundedControlBehavior widget behavior or control."""

from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty
from cooking_planner.ui.palette import PANEL_LIGHT
from cooking_planner.ui.hover_state import hover_color


class RoundedControlBehavior:
    fill_color = ListProperty(PANEL_LIGHT)

    def __init__(self, **kwargs):
        color = tuple(kwargs.pop('background_color', PANEL_LIGHT))
        kwargs['background_color'] = (0, 0, 0, 0)
        super().__init__(**kwargs)
        self._base_background = color
        self.fill_color = color
        with self.canvas.before:
            tint = Color(*color)
            shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(9)])
        self.bind(fill_color=lambda _, value: setattr(tint, 'rgba', value),
                  pos=lambda instance, _: setattr(shape, 'pos', instance.pos),
                  size=lambda instance, _: setattr(shape, 'size', instance.size))

    def _animate_background(self):
        Animation.cancel_all(self, 'fill_color')
        target = hover_color(self._base_background) if self._hovered else self._base_background
        Animation(fill_color=target, duration=0.14, t='out_quad').start(self)
