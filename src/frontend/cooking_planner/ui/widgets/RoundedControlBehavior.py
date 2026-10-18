"""RoundedControlBehavior widget behavior or control."""

from kivy.animation import Animation
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty

from cooking_planner.ui.hover_state import hover_color
from cooking_planner.ui.palette import PANEL_LIGHT


class RoundedControlBehavior:
    fill_color = ListProperty(PANEL_LIGHT)

    def __init__(self, **kwargs):
        outline_color = kwargs.pop('outline_color', None)
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
        if outline_color is not None:
            with self.canvas.after:
                outline_tint = Color(*outline_color)
                outline = Line(width=dp(1.5))

            def place_outline(*_):
                inset = dp(1)
                outline.rounded_rectangle = (self.x + inset, self.y + inset,
                                             max(0, self.width - 2 * inset),
                                             max(0, self.height - 2 * inset), dp(9))

            def update_disabled(_, disabled):
                outline_tint.rgba = (*outline_color[:3], outline_color[3] * (0.35 if disabled else 1))

            self.bind(pos=place_outline, size=place_outline)
            self.bind(disabled=update_disabled)
            place_outline()
            update_disabled(self, self.disabled)

    def _animate_background(self):
        Animation.cancel_all(self, 'fill_color')
        target = hover_color(self._base_background) if self._hovered else self._base_background
        Animation(fill_color=target, duration=0.14, t='out_quad').start(self)
