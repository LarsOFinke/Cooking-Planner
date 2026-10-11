from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from cooking_planner.ui.clipboard import get_clipboard

BG = (0.047, 0.078, 0.106, 1)
PANEL = (0.078, 0.125, 0.159, 1)
PANEL_LIGHT = (0.105, 0.165, 0.198, 1)
GOLD = (0.91, 0.72, 0.37, 1)
WHITE = (0.94, 0.95, 0.92, 1)
MUTED = (0.66, 0.73, 0.72, 1)
GREEN = (0.52, 0.78, 0.62, 1)
RED = (0.87, 0.45, 0.42, 1)


def surface(widget, color=PANEL, radius=12) -> None:
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    widget.bind(pos=lambda instance, _: setattr(shape, "pos", instance.pos),
                size=lambda instance, _: setattr(shape, "size", instance.size))


def box(vertical=True, padding=0, spacing=0, color=None, **kwargs) -> BoxLayout:
    widget = BoxLayout(orientation="vertical" if vertical else "horizontal",
                       padding=dp(padding), spacing=dp(spacing), **kwargs)
    if color is not None:
        surface(widget, color)
    return widget


def label(text, size=16, color=WHITE, height=32, bold=False, **kwargs) -> Label:
    widget = Label(text=str(text), color=color, font_size=dp(size), bold=bold,
                   size_hint_y=None, height=dp(height), halign="left", valign="middle", **kwargs)
    widget.bind(size=lambda item, _: setattr(item, "text_size", (item.width, item.height)))
    return widget


def button(text, callback=None, kind="secondary", height=42, **kwargs) -> Button:
    background = GOLD if kind == "primary" else (RED if kind == "danger" else PANEL_LIGHT)
    foreground = BG if kind == "primary" else WHITE
    widget = Button(text=text, size_hint_y=None, height=dp(height), background_normal="",
                    background_down="", background_color=background, color=foreground,
                    font_size=dp(15), **kwargs)
    if callback is not None:
        widget.bind(on_release=lambda *_: callback())
    return widget


def set_tab_active(widget: Button, text: str, active: bool) -> None:
    """Show the selected tab with color, weight, and a text marker."""
    widget.text = f"● {text}" if active else text
    widget.background_color = GOLD if active else PANEL_LIGHT
    widget.color = BG if active else MUTED
    widget.bold = active
    widget.font_size = dp(16 if active else 15)


def tab_button(text: str, callback, active=False, **kwargs) -> Button:
    widget = button(text, callback, **kwargs)
    set_tab_active(widget, text, active)
    return widget


def spinner(text, values, **kwargs) -> Spinner:
    return Spinner(text=text, values=tuple(values), size_hint_y=None, height=dp(42),
                   background_normal="", background_color=PANEL_LIGHT, color=WHITE,
                   font_size=dp(15), **kwargs)


def field(hint="", text="", multiline=False, height=42, **kwargs) -> TextInput:
    get_clipboard()
    return TextInput(text=text, hint_text=hint, multiline=multiline, size_hint_y=None,
                     height=dp(height), background_normal="", background_active="",
                     background_color=PANEL_LIGHT, foreground_color=WHITE, cursor_color=GOLD,
                     hint_text_color=MUTED, font_size=dp(15), padding=[dp(12), dp(10)], **kwargs)
