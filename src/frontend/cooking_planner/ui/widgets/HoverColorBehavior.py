"""HoverColorBehavior widget behavior or control."""

from kivy.animation import Animation
from cooking_planner.ui.palette import PANEL_LIGHT
from cooking_planner.ui.hover_state import hover_color, register


class HoverColorBehavior:
    hover_cursor = 'hand'

    def __init__(self, **kwargs):
        self._base_background = tuple(kwargs.get('background_color', PANEL_LIGHT))
        self._hovered = False
        super().__init__(**kwargs)
        register(self)
        self.bind(disabled=lambda *_: self._set_hovered(False))

    def set_base_color(self, color):
        self._base_background = tuple(color)
        self._animate_background()

    def _set_hovered(self, hovered):
        hovered = bool(hovered and not self.disabled)
        if hovered == self._hovered:
            return
        self._hovered = hovered
        self._animate_background()

    def _animate_background(self):
        Animation.cancel_all(self, 'background_color')
        target = hover_color(self._base_background) if self._hovered else self._base_background
        Animation(background_color=target, duration=0.14, t='out_quad').start(self)
