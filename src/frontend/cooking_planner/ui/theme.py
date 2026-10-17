"""Shared colors and widget construction helpers."""

from kivy.graphics import Color, RoundedRectangle
from kivy.effects.scroll import ScrollEffect
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from cooking_planner.ui.clipboard import get_clipboard
from cooking_planner.ui.hover_state import _mouse_moved as _mouse_moved
from cooking_planner.ui.palette import BG, PANEL, PANEL_LIGHT, GOLD, WHITE, MUTED, GREEN as GREEN, RED
from cooking_planner.ui.widgets.HoverButton import HoverButton
from cooking_planner.ui.widgets.HoverSpinner import HoverSpinner
from cooking_planner.ui.widgets.HoverSpinnerOption import HoverSpinnerOption
from cooking_planner.ui.widgets.HoverTextInput import HoverTextInput
from cooking_planner.ui.widgets.HoverToggleButton import HoverToggleButton as HoverToggleButton
from cooking_planner.ui.widgets.HoverSurface import HoverSurface
from cooking_planner.ui.widgets.HoverImageBehavior import HoverImageBehavior as HoverImageBehavior


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
    view = ScrollView(effect_cls=ScrollEffect, scroll_wheel_distance=dp(88), **kwargs)
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
                         font_size=dp(14), **kwargs)
    if callback is not None:
        widget.bind(on_release=lambda *_: callback())
    return widget


def set_tab_active(widget: Button, text: str, active: bool) -> None:
    """Show the selected tab with color and weight."""
    widget.text = text
    widget.set_base_color(GOLD if active else PANEL_LIGHT)
    widget.color = BG if active else MUTED
    widget.bold = active
    widget.font_size = dp(14)


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
