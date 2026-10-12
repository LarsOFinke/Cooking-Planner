"""Manage the SQLite ingredient catalog through the admin HTTP API."""

import re

from kivy.clock import Clock
from kivy.metrics import dp

from cooking_planner.ui.dialogs import confirm_popup
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, field, label, scroll_view


class IngredientAdminPanel:
    PAGE_SIZE = 40

    def __init__(self, locales, locale, on_recipes, on_search, on_save, on_delete, on_status,
                 selected=None):
        self.locales, self.locale = tuple(locales), locale
        self.on_search, self.on_save, self.on_delete = on_search, on_save, on_delete
        self.on_status = on_status
        self.selected = selected
        self.generation = 0
        self.search_event = None
        self.rows = []
        self.page = 0
        self.root = box(spacing=7)
        header = box(False, spacing=7, size_hint_y=None, height=dp(42))
        header.add_widget(label(t(locale, 'ingredient_catalog'), 19, GOLD, 42, True))
        header.add_widget(button(t(locale, 'admin_recipes'), on_recipes,
                                 size_hint_x=None, width=dp(150), height=40))
        header.add_widget(button(t(locale, 'new_ingredient'), self.new, 'primary',
                                 size_hint_x=None, width=dp(160), height=40))
        self.root.add_widget(header)
        horizontal = scroll_view(do_scroll_y=False)
        columns = box(False, spacing=7, size_hint_x=None)
        horizontal.bind(width=lambda _, width: setattr(columns, 'width', max(width, dp(790))))
        horizontal.add_widget(columns)
        left = box(padding=8, spacing=6, color=PANEL, size_hint_x=0.38)
        self.search = field(t(locale, 'search_catalog_ingredient'), height=40)
        self.search.bind(text=lambda *_: self._schedule_search())
        left.add_widget(self.search)
        pager = box(False, spacing=5, size_hint_y=None, height=dp(38))
        self.previous_button = button(t(locale, 'previous'), self.previous_page, height=38)
        self.page_label = label('', 12, WHITE, 38, True)
        self.page_label.halign = 'center'
        self.next_button = button(t(locale, 'next'), self.next_page, 'primary', height=38)
        pager.add_widget(self.previous_button)
        pager.add_widget(self.page_label)
        pager.add_widget(self.next_button)
        left.add_widget(pager)
        results_scroll = scroll_view(do_scroll_x=False)
        self.results_scroll = results_scroll
        self.results = box(spacing=5, size_hint_y=None)
        self.results.bind(minimum_height=self.results.setter('height'))
        results_scroll.add_widget(self.results)
        left.add_widget(results_scroll)
        columns.add_widget(left)
        right_scroll = scroll_view(do_scroll_x=False, size_hint_x=0.62)
        self.editor = box(padding=12, spacing=9, color=PANEL, size_hint_y=None)
        self.editor.bind(minimum_height=self.editor.setter('height'))
        right_scroll.add_widget(self.editor)
        columns.add_widget(right_scroll)
        self.root.add_widget(horizontal)
        self.status = label('', 13, MUTED, 28)
        self.root.add_widget(self.status)
        self._render_editor()
        self._schedule_search()

    def set_status(self, message):
        self.status.text = str(message)

    def _schedule_search(self):
        self.generation += 1
        self.page = 0
        if self.search_event is not None:
            self.search_event.cancel()
        generation = self.generation
        self.search_event = Clock.schedule_once(
            lambda *_: self.on_search(self.search.text.strip(),
                                     lambda rows: self._show_results(rows, generation)), 0.2)

    def _show_results(self, rows, generation):
        if generation != self.generation:
            return
        self.rows = rows
        self._render_results()

    def _render_results(self):
        total_pages = max(1, (len(self.rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(self.page, total_pages - 1)
        self.page_label.text = f"{t(self.locale, 'page')} {self.page + 1} {t(self.locale, 'of')} {total_pages}"
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page == total_pages - 1
        self.results.clear_widgets()
        self.results.add_widget(label(t(self.locale, 'ingredient_results').format(count=len(self.rows)),
                                      13, MUTED, 28))
        if not self.rows:
            self.results.add_widget(label(t(self.locale, 'no_ingredient_results'), 14, MUTED, 66))
        for row in self.rows[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            name = row['translations'].get(self.locale) or next(iter(row['translations'].values()), row['id'])
            choice = button(f"{name}\n{row['id']}", lambda entry=row: self.select(entry), height=54)
            choice.halign = 'left'
            choice.valign = 'middle'
            choice.bind(size=lambda widget, _: setattr(widget, 'text_size', (widget.width - dp(12), widget.height)))
            self.results.add_widget(choice)
        self.results_scroll.scroll_y = 1

    def previous_page(self):
        if self.page > 0:
            self.page -= 1
            self._render_results()

    def next_page(self):
        if (self.page + 1) * self.PAGE_SIZE < len(self.rows):
            self.page += 1
            self._render_results()

    def select(self, entry):
        self.selected = entry
        self._render_editor()

    def new(self):
        self.selected = None
        self._render_editor(new=True)

    def reset(self):
        self._render_editor(new=self.selected is None)

    def _cell(self, title, widget):
        cell = box(spacing=3, size_hint_y=None, height=dp(76))
        cell.add_widget(label(title, 13, MUTED, 24))
        cell.add_widget(widget)
        self.editor.add_widget(cell)

    def _render_editor(self, new=False):
        self.editor.clear_widgets()
        if self.selected is None and not new:
            self.editor.add_widget(label(t(self.locale, 'select_ingredient'), 16, MUTED, 80))
            return
        entry = self.selected or {'id': '', 'translations': {}}
        self.editor.add_widget(label(t(self.locale, 'new_ingredient' if new else 'edit_ingredient'),
                                     18, GOLD, 36, True))
        self.id_input = field(t(self.locale, 'admin_ingredient_id'), text=entry['id'])
        self.id_input.readonly = not new
        self._cell(t(self.locale, 'admin_ingredient_id'), self.id_input)
        self.names = {}
        for code in self.locales:
            widget = field(t(self.locale, 'admin_ingredient_name'),
                           text=entry['translations'].get(code, ''))
            self.names[code] = widget
            self._cell(f"{t(self.locale, 'admin_ingredient_name')} · {code.upper()}", widget)
        self.editor.add_widget(label(t(self.locale, 'ingredient_language_help'), 13, MUTED, 62))
        actions = box(False, spacing=8, size_hint_y=None, height=dp(42))
        actions.add_widget(button(t(self.locale, 'save_ingredient'), self.save, 'primary', height=42))
        actions.add_widget(button(t(self.locale, 'admin_reset'), self.reset, height=42))
        if not new:
            actions.add_widget(button(t(self.locale, 'delete_ingredient'), self.confirm_delete,
                                      'danger', height=42))
        self.editor.add_widget(actions)

    def save(self):
        ingredient_id = self.id_input.text.strip()
        names = {code: widget.text.strip() for code, widget in self.names.items()}
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', ingredient_id) or len(ingredient_id) > 120:
            self.set_status(t(self.locale, 'invalid_ingredient_id'))
            return
        if not any(names.values()) or any(len(name) > 180 for name in names.values()):
            self.set_status(t(self.locale, 'ingredient_name_required'))
            return
        self.on_save(ingredient_id, names)

    def confirm_delete(self):
        ingredient_id = self.selected['id']
        confirm_popup(t(self.locale, 'delete_ingredient_question'), self.locale,
                      lambda: self.on_delete(ingredient_id),
                      title=t(self.locale, 'delete_ingredient'),
                      confirm_label=t(self.locale, 'delete_ingredient'))
