"""HoverImageBehavior widget behavior or control."""

from kivy.animation import Animation

from cooking_planner.ui.hover_state import register


class HoverImageBehavior:
    hover_cursor = 'hand'

    def __init__(self, **kwargs):
        self._hovered = False
        super().__init__(**kwargs)
        register(self)

    def _set_hovered(self, hovered):
        hovered = bool(hovered and not self.disabled)
        if hovered == self._hovered:
            return
        self._hovered = hovered
        Animation.cancel_all(self, 'opacity')
        Animation(opacity=0.82 if hovered else 1, duration=0.14, t='out_quad').start(self)
