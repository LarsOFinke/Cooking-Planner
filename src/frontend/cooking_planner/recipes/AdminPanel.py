"""Catalog-backed recipe editor; writes are handled by the backend API."""

from copy import deepcopy
from kivy.clock import Clock
from kivy.metrics import dp
from cooking_planner.recipes.AdminFormPages import AdminFormPages
from cooking_planner.recipes.admin_payload import (FormError, RecipeFormSnapshot,
                                                    build_submission)
from cooking_planner.recipes.admin_schema import CHOICES, TIMES
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import (GOLD, MUTED, PANEL, PANEL_LIGHT, box, button,
                                      field, label, scroll_view, spinner)

class AdminPanel(AdminFormPages):
    def cancel_pending(self):
        self._list_search.cancel()
        for event in (self._list_event, self.search_event):
            if event is not None:
                event.cancel()
        self._list_event = None
        self.search_event = None

    def __init__(self, records, locales, locale, on_select, on_save, on_delete, on_reload, on_status,
                 options=None, status_message=None, on_ingredient_search=None, on_ingredient_admin=None):
        self.records, self.locales, self.locale = records, tuple(locales), locale
        self.on_select, self.on_save = on_select, on_save
        self.on_delete, self.on_reload, self.on_status = on_delete, on_reload, on_status
        self.options = options or {}
        self.on_ingredient_search = on_ingredient_search
        self.search_generation = 0
        self.search_event = None
        self._list_event = None
        self._list_search = Clock.create_trigger(lambda *_: self._render_list(), 0.18)
        self.status_message = status_message or t(locale, 'ready')
        self.entry, self.creating, self.page = None, False, 'details'
        self.root = box(spacing=6)
        header_scroll = scroll_view(do_scroll_y=False, size_hint_y=None, height=dp(42))
        header = box(False, spacing=7, size_hint_x=None, size_hint_y=None, height=dp(42))
        header_scroll.bind(width=lambda _, width: setattr(header, 'width', max(width, dp(650))))
        header.add_widget(label(t(locale, 'admin'), 19, GOLD, 42, True))
        header.add_widget(button(t(locale, 'admin_new'), self.new, 'primary',
                                 size_hint_x=None, width=dp(130), height=40))
        if on_ingredient_admin is not None:
            header.add_widget(button(t(locale, 'ingredient_catalog'), on_ingredient_admin,
                                     size_hint_x=None, width=dp(170), height=40))
        header.add_widget(button(t(locale, 'refresh'), on_reload,
                                 size_hint_x=None, width=dp(95), height=40))
        header_scroll.add_widget(header)
        self.root.add_widget(header_scroll)
        horizontal = scroll_view(do_scroll_y=False)
        self.horizontal = horizontal
        columns = box(False, spacing=6, size_hint_x=None)
        self.columns = columns
        horizontal.bind(width=lambda _, width: setattr(columns, 'width', max(width, dp(500))))
        horizontal.add_widget(columns)
        self.root.add_widget(horizontal)
        left = box(padding=6, spacing=5, color=PANEL, size_hint_x=0.28)
        self.search = field(t(locale, 'admin_search'), height=38)
        self.search.bind(text=lambda *_: self._list_search())
        left.add_widget(self.search)
        list_scroll = scroll_view(do_scroll_x=False)
        self.list_rows = box(spacing=4, size_hint_y=None)
        self.list_rows.bind(minimum_height=self.list_rows.setter('height'))
        list_scroll.add_widget(self.list_rows)
        left.add_widget(list_scroll)
        columns.add_widget(left)
        right = box(spacing=5, size_hint_x=0.72)
        self.toolbar = box(False, spacing=5, size_hint_y=None, height=dp(38))
        right.add_widget(self.toolbar)
        editor_scroll = scroll_view(do_scroll_x=False)
        self.form = box(padding=8, color=PANEL, size_hint_y=None)
        self.form.bind(minimum_height=self.form.setter('height'))
        editor_scroll.add_widget(self.form)
        right.add_widget(editor_scroll)
        self.actions = box(False, spacing=6, size_hint_y=None, height=dp(40))
        right.add_widget(self.actions)
        columns.add_widget(right)
        self._render_list()
        self._render_form()

    def _render_list(self):
        self._list_search.cancel()
        if self._list_event is not None:
            self._list_event.cancel()
            self._list_event = None
        self.list_rows.clear_widgets()
        query = self.search.text.casefold().strip()
        matches = [record for record in self.records if query in
                   (record['id'] + ' ' + ' '.join(record['names'].values())).casefold()]
        self.list_rows.add_widget(label(f"{len(matches)} {t(self.locale, 'results')}", 13, MUTED, 28))
        remaining = matches[:80]

        def append_batch(_):
            for record in remaining[:20]:
                name = record['names'].get(self.locale) or next(iter(record['names'].values()), '')
                item = button(f"{name}\n{record['id']}",
                              lambda recipe_id=record['id']: self.on_select(recipe_id),
                              'primary' if self.entry and record['id'] == self.entry['id'] else 'secondary',
                              height=52)
                item.halign = 'left'
                item.valign = 'middle'
                item.shorten = True
                item.bind(size=lambda widget, _: setattr(widget, 'text_size',
                                                         (widget.width - dp(12), widget.height)))
                self.list_rows.add_widget(item)
            del remaining[:20]
            self._list_event = Clock.schedule_once(append_batch, 0) if remaining else None

        append_batch(0)

    def show_recipe(self, entry):
        self.entry, self.creating = deepcopy(entry), False
        self.page = 'details'
        self._render_list()
        self._render_form()
        self.horizontal.scroll_x = 1

    def new(self):
        self.entry, self.creating = None, True
        self.page = 'details'
        self._render_list()
        self._render_form()
        self.horizontal.scroll_x = 1

    def reset(self):
        self._render_form()

    def set_status(self, message):
        self.status_message = message
        if hasattr(self, 'status_text'):
            self.status_text.text = message

    def _schedule_ingredient_search(self):
        self.search_generation += 1
        if self.search_event is not None:
            self.search_event.cancel()
        query = self.ingredient_search.text.strip()
        self.ingredient_matches.clear_widgets()
        if len(query) < 2 or self.on_ingredient_search is None:
            return
        generation = self.search_generation
        locale = self.edit_locale
        self.search_event = Clock.schedule_once(
            lambda *_: self.on_ingredient_search(locale, query,
                lambda matches: self._show_ingredient_matches(matches, generation)), 0.25)

    def _show_ingredient_matches(self, matches, generation):
        if generation != self.search_generation:
            return
        self.ingredient_matches.clear_widgets()
        for match in matches[:8]:
            self.ingredient_matches.add_widget(button(
                f"{match['name']} · {match['id']}",
                lambda selected=match: self._select_ingredient(selected), height=36))

    def _select_ingredient(self, match):
        reusable = next((entry for entry in self.ingredient_rows if
                         entry['shared']['ingredient_id'].text.strip() in ('', 'ingredient-id')), None)
        if reusable is None:
            self.add_ingredient()
            reusable = self.ingredient_rows[-1]
        reusable['shared']['ingredient_id'].text = match['id']
        for code, widget in reusable['names'].items():
            widget.text = match['translations'].get(code, '')
        self.ingredient_search.text = ''
        self.ingredient_matches.clear_widgets()

    def _add_ingredient(self, ingredient, names):
        card = box(padding=8, spacing=5, color=PANEL_LIGHT, size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        heading = self._row(card, 35)
        title = label('', 15, GOLD, 35, True)
        heading.add_widget(title)
        heading.add_widget(button(t(self.locale, 'admin_remove_ingredient'),
                                  lambda: self._remove_ingredient(entry), 'danger',
                                  size_hint_x=None, width=dp(120), height=35))
        shared_row = self._row(card)
        shared = {
            'ingredient_id': self._cell(shared_row, t(self.locale, 'admin_ingredient_id'),
                                        field(text=ingredient.get('ingredient_id', ''))),
            'amount': self._cell(shared_row, t(self.locale, 'admin_amount'),
                                 field(text=str(ingredient.get('amount', 1)))),
            'unit': self._cell(shared_row, t(self.locale, 'admin_unit'),
                               spinner(ingredient.get('unit', 'g'), ('g', 'ml', 'pcs'))),
        }
        name_sections, name_inputs = {}, {}
        for code in self.locales:
            section = box(size_hint_y=None, height=dp(72))
            name_inputs[code] = self._cell(section, t(self.locale, 'admin_ingredient_name') + ' · ' + code.upper(),
                                           field(text=names.get(code, '')))
            name_sections[code] = section
            card.add_widget(section)
        entry = {'card': card, 'title': title, 'original': deepcopy(ingredient),
                 'shared': shared, 'names': name_inputs, 'name_sections': name_sections}
        self.ingredient_rows.append(entry)
        self.ingredients_container.add_widget(card)
        self._number_ingredients()
        self._change_language(self.edit_locale)

    def add_ingredient(self):
        self._add_ingredient({'ingredient_id': '', 'amount': 1, 'unit': 'g'},
                             {code: '' for code in self.locales})

    def _remove_ingredient(self, entry):
        self.ingredients_container.remove_widget(entry['card'])
        self.ingredient_rows.remove(entry)
        self._number_ingredients()

    def _number_ingredients(self):
        for index, entry in enumerate(self.ingredient_rows, 1):
            entry['title'].text = f"{t(self.locale, 'admin_ingredient')} {index}"

    def _add_step(self, step, texts):
        card = box(padding=8, spacing=5, color=PANEL_LIGHT, size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        heading = self._row(card, 35)
        title = label('', 15, GOLD, 35, True)
        heading.add_widget(title)
        heading.add_widget(button(t(self.locale, 'admin_remove_ingredient'),
                                  lambda: self._remove_step(entry), 'danger',
                                  size_hint_x=None, width=dp(120), height=35))
        ids = self._cell(card, t(self.locale, 'admin_step_ingredients'),
                         field(text=', '.join(step.get('ingredient_ids', []))))
        text_sections, text_inputs = {}, {}
        for code in self.locales:
            section = box(size_hint_y=None, height=dp(112))
            text_inputs[code] = self._cell(section, t(self.locale, 'admin_step_text') + ' · ' + code.upper(),
                                            field(text=texts.get(code, ''), multiline=True, height=88), 112)
            text_sections[code] = section
            card.add_widget(section)
        entry = {'card': card, 'title': title, 'ids': ids,
                 'texts': text_inputs, 'text_sections': text_sections}
        self.step_rows.append(entry)
        self.steps_container.add_widget(card)
        self._number_steps()

    def add_step(self):
        self._add_step({'ingredient_ids': []}, {code: '' for code in self.locales})
        self._change_language(self.edit_locale)

    def _remove_step(self, entry):
        self.steps_container.remove_widget(entry['card'])
        self.step_rows.remove(entry)
        self._number_steps()

    def _number_steps(self):
        for index, entry in enumerate(self.step_rows, 1):
            entry['title'].text = f"{t(self.locale, 'instruction_step')} {index}"

    def save(self):
        snapshot = RecipeFormSnapshot(
            recipe_id=self.id_input.text, source=self.source.text, locale=self.locale,
            locales=self.locales,
            choices={code: widget.text for code, widget in self.locale_choices.items()},
            shared_choices={key: self._value(self.shared_inputs[key]) for key, _ in CHOICES},
            times={key: self.shared_inputs[key].text for key, _ in TIMES},
            diets=[code for code, widget in self.diet_buttons.items() if widget.activated],
            images=self.shared_inputs['images'].text,
            ingredients=[{'original': entry['original'],
                          'ingredient_id': entry['shared']['ingredient_id'].text,
                          'amount': entry['shared']['amount'].text,
                          'unit': entry['shared']['unit'].text,
                          'names': {code: widget.text for code, widget in entry['names'].items()}}
                         for entry in self.ingredient_rows],
            steps=[{'ingredient_ids': entry['ids'].text,
                    'texts': {code: widget.text for code, widget in entry['texts'].items()}}
                   for entry in self.step_rows],
            names={code: widgets['name'].text for code, widgets in self.locale_inputs.items()},
            documents=self.documents, options=self.options,
        )
        try:
            recipe_id, source, translations = build_submission(snapshot)
        except FormError as error:
            self.on_status(str(error))
            return
        self.on_save(recipe_id, source, translations, self.creating)
