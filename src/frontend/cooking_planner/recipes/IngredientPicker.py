"""Paged catalog chooser for recipe ingredients."""

from kivy.metrics import dp
from kivy.uix.popup import Popup

from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import GOLD, MUTED, box, button, field, label, scroll_view


class IngredientPicker(Popup):
    PAGE_SIZE = 40

    def __init__(self, catalog, locale, edit_locale, on_select, **kwargs):
        self.catalog = catalog
        self.locale = locale
        self.edit_locale = edit_locale
        self.on_select = on_select
        self.page = 0
        content = box(padding=8, spacing=6)
        self.query = field(t(locale, 'admin_filter_ingredients'), height=40)
        content.add_widget(self.query)
        self.list_scroll = scroll_view(do_scroll_x=False)
        self.choices = box(spacing=3, size_hint_y=None)
        self.choices.bind(minimum_height=self.choices.setter('height'))
        self.list_scroll.add_widget(self.choices)
        content.add_widget(self.list_scroll)
        navigation = box(False, spacing=6, size_hint_y=None, height=dp(40))
        self.previous = button(t(locale, 'previous'), lambda: self.move(-1), height=40)
        self.position = label('', 13, GOLD, 40, True)
        self.next_button = button(t(locale, 'next'), lambda: self.move(1), height=40)
        for widget in (self.previous, self.position, self.next_button):
            navigation.add_widget(widget)
        content.add_widget(navigation)
        super().__init__(title=t(locale, 'admin_choose_ingredient'), content=content,
                         size_hint=(0.85, 0.85), **kwargs)
        self.query.bind(text=self._filter_changed)
        self.render()

    def _name(self, entry):
        return (entry['translations'].get(self.edit_locale)
                or next(iter(entry['translations'].values()), entry['id']))

    def _filter_changed(self, *_):
        self.page = 0
        self.render()

    def move(self, delta):
        self.page += delta
        self.render()

    def render(self):
        needle = self.query.text.strip().casefold()
        rows = [row for row in self.catalog if
                not needle or needle in row['id'].casefold() or
                any(needle in name.casefold() for name in row['translations'].values())]
        rows.sort(key=lambda row: self._name(row).casefold())
        last = max(0, (len(rows) - 1) // self.PAGE_SIZE)
        self.page = min(max(0, self.page), last)
        self.position.text = f'{self.page + 1} / {last + 1} · {len(rows)}'
        self.previous.disabled = self.page == 0
        self.next_button.disabled = self.page == last
        self.choices.clear_widgets()
        for row in rows[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            self.choices.add_widget(button(self._name(row), lambda entry=row: self.choose(entry), height=38))
        if not rows:
            self.choices.add_widget(label(t(self.locale, 'no_ingredient_results'), 14, MUTED, 60))
        self.list_scroll.scroll_y = 1

    def choose(self, entry):
        self.on_select(entry)
        self.dismiss()
