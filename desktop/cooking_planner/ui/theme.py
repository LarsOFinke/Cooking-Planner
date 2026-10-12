from weakref import WeakSet

from kivy.animation import Animation
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.effects.scroll import ScrollEffect
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

from cooking_planner.ui.clipboard import get_clipboard

BG = (0.047, 0.078, 0.106, 1)
PANEL = (0.078, 0.125, 0.159, 1)
PANEL_LIGHT = (0.105, 0.165, 0.198, 1)
GOLD = (0.91, 0.72, 0.37, 1)
WHITE = (0.94, 0.95, 0.92, 1)
MUTED = (0.66, 0.73, 0.72, 1)
GREEN = (0.52, 0.78, 0.62, 1)
RED = (0.87, 0.45, 0.42, 1)

_hover_widgets = WeakSet()
_hover_bound = False
_cursor = 'arrow'


def _hover_color(color):
    if color[3] < 0.1:
        return (*PANEL_LIGHT[:3], 0.85)
    return tuple(min(1, value + (1 - value) * 0.16) for value in color[:3]) + (color[3],)


def _within_visible_area(widget, position, top):
    node = widget
    while node is not None and node is not Window:
        if node.opacity == 0:
            return False
        if node is widget or isinstance(node, ScrollView):
            if not node.collide_point(*node.to_widget(*position)):
                return False
        if node is top:
            return True
        node = node.parent
    return False


def _mouse_moved(_window, position):
    global _cursor
    top = Window.children[0] if Window.children else None
    cursor = 'arrow'
    for widget in tuple(_hover_widgets):
        inside = (top is not None and not widget.disabled and widget.get_root_window() is Window
                  and _within_visible_area(widget, position, top))
        widget._set_hovered(inside)
        if inside:
            if widget.hover_cursor == 'ibeam' or cursor == 'arrow':
                cursor = widget.hover_cursor
    if cursor != _cursor:
        Window.set_system_cursor(cursor)
        _cursor = cursor


class HoverColorBehavior:
    hover_cursor = 'hand'

    def __init__(self, **kwargs):
        global _hover_bound
        self._base_background = tuple(kwargs.get('background_color', PANEL_LIGHT))
        self._hovered = False
        super().__init__(**kwargs)
        _hover_widgets.add(self)
        if not _hover_bound:
            Window.bind(mouse_pos=_mouse_moved)
            _hover_bound = True
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
        target = _hover_color(self._base_background) if self._hovered else self._base_background
        Animation(background_color=target, duration=0.14, t='out_quad').start(self)


class HoverButton(HoverColorBehavior, Button):
    pass


class HoverSpinner(HoverColorBehavior, Spinner):
    pass


class HoverSpinnerOption(HoverColorBehavior, SpinnerOption):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('background_color', PANEL_LIGHT)
        kwargs.setdefault('color', WHITE)
        super().__init__(**kwargs)


class HoverTextInput(HoverColorBehavior, TextInput):
    hover_cursor = 'ibeam'


class HoverToggleButton(HoverColorBehavior, ToggleButton):
    pass


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


class HoverImageBehavior:
    hover_cursor = 'hand'

    def __init__(self, **kwargs):
        global _hover_bound
        self._hovered = False
        super().__init__(**kwargs)
        _hover_widgets.add(self)
        if not _hover_bound:
            Window.bind(mouse_pos=_mouse_moved)
            _hover_bound = True

    def _set_hovered(self, hovered):
        hovered = bool(hovered and not self.disabled)
        if hovered == self._hovered:
            return
        self._hovered = hovered
        Animation.cancel_all(self, 'opacity')
        Animation(opacity=0.82 if hovered else 1, duration=0.14, t='out_quad').start(self)


def surface(widget, color=PANEL, radius=12) -> None:
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    widget.bind(pos=lambda instance, _: setattr(shape, "pos", instance.pos),
                size=lambda instance, _: setattr(shape, "size", instance.size))


def box(vertical=True, padding=0, spacing=0, color=None, hover=False, **kwargs) -> BoxLayout:
    options = dict(orientation="vertical" if vertical else "horizontal",
                   padding=dp(padding), spacing=dp(spacing), **kwargs)
    widget = HoverSurface(background_color=color, **options) if hover and color is not None else BoxLayout(**options)
    if color is not None and not hover:
        surface(widget, color)
    return widget


def scroll_view(**kwargs) -> ScrollView:
    view = ScrollView(effect_cls=ScrollEffect, scroll_wheel_distance=dp(22), **kwargs)
    for effect in (view.effect_x, view.effect_y):
        if effect is not None:
            effect.friction = 0.18
    return view


def label(text, size=16, color=WHITE, height=32, bold=False, **kwargs) -> Label:
    widget = Label(text=str(text), color=color, font_size=dp(size), bold=bold,
                   size_hint_y=None, height=dp(height), halign="left", valign="middle", **kwargs)
    widget.bind(size=lambda item, _: setattr(item, "text_size", (item.width, item.height)))
    return widget


def button(text, callback=None, kind="secondary", height=42, **kwargs) -> Button:
    background = GOLD if kind == "primary" else (RED if kind == "danger" else PANEL_LIGHT)
    foreground = BG if kind == "primary" else WHITE
    widget = HoverButton(text=text, size_hint_y=None, height=dp(height), background_normal="",
                         background_down="", background_color=background, color=foreground,
                         font_size=dp(15), **kwargs)
    if callback is not None:
        widget.bind(on_release=lambda *_: callback())
    return widget


def set_tab_active(widget: Button, text: str, active: bool) -> None:
    """Show the selected tab with color and weight."""
    widget.text = text
    widget.set_base_color(GOLD if active else PANEL_LIGHT)
    widget.color = BG if active else MUTED
    widget.bold = active
    widget.font_size = dp(16 if active else 15)


def tab_button(text: str, callback, active=False, **kwargs) -> Button:
    widget = button(text, callback, **kwargs)
    set_tab_active(widget, text, active)
    return widget


def spinner(text, values, **kwargs) -> Spinner:
    return HoverSpinner(text=text, values=tuple(values), option_cls=HoverSpinnerOption,
                        size_hint_y=None, height=dp(42), background_normal="",
                        background_color=PANEL_LIGHT, color=WHITE, font_size=dp(15), **kwargs)


def field(hint="", text="", multiline=False, height=42, **kwargs) -> TextInput:
    get_clipboard()
    return HoverTextInput(text=text, hint_text=hint, multiline=multiline, size_hint_y=None,
                          height=dp(height), background_normal="", background_active="",
                          background_color=PANEL_LIGHT, foreground_color=WHITE, cursor_color=GOLD,
                          hint_text_color=MUTED, font_size=dp(15), padding=[dp(12), dp(10)], **kwargs)
