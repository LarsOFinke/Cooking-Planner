"""Shared pointer tracking for hoverable Kivy controls."""

from weakref import WeakSet

from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.palette import PANEL_LIGHT

_hover_widgets = WeakSet()
_hover_bound = False
_cursor = 'arrow'


def hover_color(color):
    if color[3] < 0.1:
        return (*PANEL_LIGHT[:3], 0.85)
    return tuple(min(1, value + (1 - value) * 0.16) for value in color[:3]) + (color[3],)


def _within_visible_area(widget, position, top):
    node = widget
    while node is not None and node is not Window:
        if node.opacity == 0:
            return False
        if node is widget or isinstance(node, ScrollView):
            parent_position = node.parent.to_widget(*position) if node.parent is not Window else position
            if not node.collide_point(*parent_position):
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


def register(widget):
    global _hover_bound
    _hover_widgets.add(widget)
    if not _hover_bound:
        Window.bind(mouse_pos=_mouse_moved)
        _hover_bound = True
