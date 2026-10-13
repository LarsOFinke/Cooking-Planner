"""Recipe admin form layout, tabs, and language rendering."""

from copy import deepcopy
from kivy.metrics import dp
from cooking_planner.recipes.admin_payload import option_labels
from cooking_planner.recipes.admin_schema import CHOICES, LABELS, TIMES, new_recipe_template, translation_template
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import (GOLD, MUTED, PANEL_LIGHT, WHITE, box, button,
                                      field, label, set_tab_active, spinner, tab_button,
                                      HoverToggleButton)


class AdminFormPages:
    def _cell(self, parent, title, widget, height=72):
        cell = box(spacing=2, size_hint_y=None, height=dp(height))
        cell.add_widget(label(title, 13, MUTED, 24))
        cell.add_widget(widget)
        parent.add_widget(cell)
        return widget

    def _row(self, parent, height=72):
        row = box(False, spacing=8, size_hint_y=None, height=dp(height))
        parent.add_widget(row)
        return row

    def _heading(self, parent, key):
        parent.add_widget(label(t(self.locale, key), 17, GOLD, 30, True))

    def _options(self, key, locale):
        return option_labels(self.options, key, locale)

    def _set_choice(self, widget, key, value):
        choices = self._options(key, self.edit_locale)
        if value and value not in choices:
            choices[value] = value
        widget._codes = {f'{name} · {code}': code for code, name in choices.items()}
        widget.values = tuple(sorted(widget._codes, key=str.casefold))
        widget.text = next((name for name, code in widget._codes.items() if code == value),
                           t(self.locale, 'admin_select_option'))

    def _choice(self, key, value):
        widget = spinner('', ())
        self._set_choice(widget, key, value)
        return widget

    @staticmethod
    def _value(widget):
        return widget._codes.get(widget.text, '')

    def _render_form(self):
        self.search_generation += 1
        if self.search_event is not None:
            self.search_event.cancel()
            self.search_event = None
        self.form.clear_widgets()
        self.toolbar.clear_widgets()
        self.actions.clear_widgets()
        self.shared_inputs, self.locale_inputs, self.locale_choices = {}, {}, {}
        self.ingredient_rows = []
        self._render_status_page()
        if not self.creating and self.entry is None:
            self.select_page = box(padding=10, color=PANEL_LIGHT,
                                   size_hint_y=None, height=dp(80))
            self.select_page.add_widget(label(t(self.locale, 'admin_select'), 15, MUTED, 60))
            self._show_page(self.page if self.page == 'status' else 'details')
            return
        recipe_id = '' if self.creating else self.entry['id']
        source = self.locale if self.locale in self.locales else self.locales[0]
        if not self.creating and self.entry['translations'].get(source) is None:
            source = next((code for code in self.locales if self.entry['translations'].get(code)), source)
        source_document = (self.entry['translations'][source] if not self.creating
                           else new_recipe_template(recipe_id))
        self.documents = {}
        for code in self.locales:
            existing = None if self.creating else self.entry['translations'].get(code)
            self.documents[code] = deepcopy(existing) if existing else translation_template(source_document)
        self.edit_locale = source
        self.source = spinner(source.upper(), (code.upper() for code in self.locales))
        self.language = spinner(source.upper(), (code.upper() for code in self.locales),
                                size_hint_x=None, width=dp(68))
        self.language.bind(text=lambda *_: self._change_language(self.language.text.lower()))
        self.page_titles.update({'details': 'admin_details_tab', 'ingredients': 'admin_ingredients_short',
                                 'recipe': 'admin_recipe_tab'})
        for page in ('details', 'ingredients', 'recipe'):
            title = self.page_titles[page]
            control = tab_button(t(self.locale, title), lambda selected=page: self._show_page(selected),
                                 page == self.page, height=38)
            self.page_tabs[page] = control
            self.toolbar.add_widget(control)
        self.toolbar.add_widget(self.language)
        self.details = box(spacing=8, size_hint_y=None)
        self.details.bind(minimum_height=self.details.setter('height'))
        self.ingredients_page = box(spacing=8, size_hint_y=None)
        self.ingredients_page.bind(minimum_height=self.ingredients_page.setter('height'))
        self.recipe_page = box(spacing=10, size_hint_y=None)
        self.recipe_page.bind(minimum_height=self.recipe_page.setter('height'))
        self._render_recipe_page(source_document)
        self._render_details_page(recipe_id, source, source_document)
        self._render_ingredients_page(source_document)
        self._change_language(source)
        self._show_page(self.page)
        self.actions.add_widget(button(t(self.locale, 'admin_create' if self.creating else 'admin_update'),
                                       self.save, 'primary', height=40))
        self.actions.add_widget(button(t(self.locale, 'admin_reset'), self.reset, height=40))
        if not self.creating:
            self.actions.add_widget(button(t(self.locale, 'admin_delete'),
                                           lambda: self.on_delete(self.entry['id']), 'danger', height=40))

    def _render_status_page(self):
        self.status_page = box(spacing=8, size_hint_y=None)
        self.status_page.bind(minimum_height=self.status_page.setter('height'))
        self._heading(self.status_page, 'admin_status')
        stats = box(False, spacing=7, size_hint_y=None, height=dp(64))
        for value, caption in ((len(self.records), 'recipes_count'),
                               (len(self.locales), 'admin_languages')):
            tile = box(padding=7, spacing=0, color=PANEL_LIGHT)
            tile.add_widget(label(str(value), 20, GOLD, 29, True))
            tile.add_widget(label(t(self.locale, caption), 12, MUTED, 22))
            stats.add_widget(tile)
        self.status_page.add_widget(stats)
        status_card = box(padding=9, spacing=3, color=PANEL_LIGHT,
                          size_hint_y=None, height=dp(80))
        status_card.add_widget(label(t(self.locale, 'admin_latest_status'), 14, GOLD, 24, True))
        self.status_text = label(self.status_message, 14, WHITE, 42)
        status_card.add_widget(self.status_text)
        self.status_page.add_widget(status_card)
        self.page_titles = {'status': 'admin_status_short'}
        self.page_tabs = {'status': tab_button(t(self.locale, 'admin_status_short'),
                                               lambda: self._show_page('status'), self.page == 'status',
                                               height=38)}
        self.toolbar.add_widget(self.page_tabs['status'])

    def _render_recipe_page(self, source_document):
        self.recipe_title = label('', 15, GOLD, 26, True)
        self.recipe_page.add_widget(self.recipe_title)
        self.step_rows = []
        self.steps_container = box(spacing=7, size_hint_y=None)
        self.steps_container.bind(minimum_height=self.steps_container.setter('height'))
        self.recipe_page.add_widget(self.steps_container)
        source_steps = source_document.get('instructions', {}).get('steps', [])
        for index, step in enumerate(source_steps):
            texts = {code: (self.documents[code].get('instructions', {}).get('steps', [])[index].get('text', '')
                            if index < len(self.documents[code].get('instructions', {}).get('steps', [])) else '')
                     for code in self.locales}
            self._add_step(step, texts)
        self.recipe_page.add_widget(button(t(self.locale, 'admin_add_step'), self.add_step,
                                           size_hint_x=None, width=dp(180)))

    def _render_details_page(self, recipe_id, source, source_document):
        self._heading(self.details, 'admin_details')
        identity = self._row(self.details)
        self.id_input = self._cell(identity, t(self.locale, 'admin_id'), field(text=recipe_id))
        self.id_input.readonly = not self.creating
        self._cell(identity, t(self.locale, 'admin_source'), self.source)
        self._heading(self.details, 'admin_languages')
        language_row = self._row(self.details)
        for code in self.locales:
            existing = None if self.creating else self.entry['translations'].get(code)
            mode = (t(self.locale, 'admin_translate') if (self.creating and code == source) or existing
                    else t(self.locale, 'admin_choose') if self.creating else t(self.locale, 'admin_omit'))
            choice = spinner(mode, (t(self.locale, 'admin_choose'), t(self.locale, 'admin_translate'),
                                    t(self.locale, 'admin_omit')))
            self.locale_choices[code] = self._cell(language_row, code.upper(), choice)
        self._heading(self.details, 'admin_translation')
        self.name_sections = {}
        for code in self.locales:
            section = box(size_hint_y=None, height=dp(72))
            name = self._cell(section, t(self.locale, 'admin_name') + ' · ' + code.upper(),
                              field(text=self.documents[code].get('name', '')))
            self.locale_inputs[code] = {'name': name}
            self.name_sections[code] = section
            self.details.add_widget(section)
        self._heading(self.details, 'admin_shared_fields')
        for offset in range(0, len(CHOICES), 2):
            row = self._row(self.details)
            for key, title in CHOICES[offset:offset + 2]:
                self.shared_inputs[key] = self._cell(row, t(self.locale, title),
                                                      self._choice(key, source_document.get(key, '')))
        diets = self._options('suitable_for', source)
        selected = source_document.get('suitable_for', [])
        self.diet_buttons = {}
        self._heading(self.details, 'admin_suitable_for')
        diet_row = self._row(self.details, 44)
        for value in dict.fromkeys([*diets, *selected]):
            toggle = HoverToggleButton(text=diets.get(value, value), activated=value in selected,
                                       size_hint_y=None, height=dp(42), background_normal='',
                                       background_down='', background_color=PANEL_LIGHT, color=WHITE,
                                       font_size=dp(13))
            self.diet_buttons[value] = toggle
            diet_row.add_widget(toggle)
        self._heading(self.details, 'admin_time_and_images')
        times = self._row(self.details)
        for key, title in TIMES:
            self.shared_inputs[key] = self._cell(times, t(self.locale, title),
                                                  field(text=str(source_document.get(key, 0))))
        images = '\n'.join(source_document.get('images', []))
        self.shared_inputs['images'] = self._cell(self.details, t(self.locale, 'admin_images'),
                                                   field(text=images, multiline=True, height=dp(65)), 94)

    def _render_ingredients_page(self, source_document):
        self._heading(self.ingredients_page, 'admin_ingredients')
        self.ingredient_search = field(t(self.locale, 'admin_search_ingredient'), height=38)
        self.ingredient_search.bind(text=lambda *_: self._schedule_ingredient_search())
        self.ingredients_page.add_widget(self.ingredient_search)
        self.ingredient_matches = box(spacing=3, size_hint_y=None)
        self.ingredient_matches.bind(minimum_height=self.ingredient_matches.setter('height'))
        self.ingredients_page.add_widget(self.ingredient_matches)
        self.ingredients_container = box(spacing=7, size_hint_y=None)
        self.ingredients_container.bind(minimum_height=self.ingredients_container.setter('height'))
        self.ingredients_page.add_widget(self.ingredients_container)
        for ingredient in source_document.get('ingredients', []):
            ingredient_id = ingredient.get('ingredient_id', '')
            names = {code: next((item.get('name', '') for item in self.documents[code].get('ingredients', [])
                                 if item.get('ingredient_id') == ingredient_id), '') for code in self.locales}
            self._add_ingredient(ingredient, names)
        self.ingredients_page.add_widget(button(t(self.locale, 'admin_add_ingredient'), self.add_ingredient,
                                                size_hint_x=None, width=dp(200)))

    def _show_page(self, page):
        self.page = page
        for name, control in self.page_tabs.items():
            set_tab_active(control, t(self.locale, self.page_titles[name]), name == page)
        if hasattr(self, 'recipe_title') and self.locale_inputs:
            self.recipe_title.text = (self.locale_inputs[self.edit_locale]['name'].text.strip()
                                      or t(self.locale, 'admin_unnamed_recipe'))
        self.form.clear_widgets()
        pages = {'status': self.status_page}
        if self.creating or self.entry is not None:
            pages.update(details=self.details, ingredients=self.ingredients_page, recipe=self.recipe_page)
        else:
            pages['details'] = self.select_page
        self.form.add_widget(pages[page])
        self.actions.height = dp(40) if page != 'status' and (self.creating or self.entry) else 0
        self.actions.opacity = 1 if self.actions.height else 0

    def _change_language(self, code):
        if code not in self.locales:
            return
        self.edit_locale = code
        self.recipe_title.text = (self.locale_inputs[code]['name'].text.strip()
                                  or t(self.locale, 'admin_unnamed_recipe'))
        for language, section in self.name_sections.items():
            section.height = dp(72) if language == code else 0
            section.opacity = 1 if language == code else 0
            section.disabled = language != code
        for key, widget in self.shared_inputs.items():
            if key in LABELS:
                self._set_choice(widget, key, self._value(widget))
        for value, toggle in self.diet_buttons.items():
            toggle.text = self._options('suitable_for', code).get(value, value)
        for entry in self.ingredient_rows:
            for language, section in entry['name_sections'].items():
                section.height = dp(72) if language == code else 0
                section.opacity = 1 if language == code else 0
                section.disabled = language != code
        for entry in self.step_rows:
            for language, section in entry['text_sections'].items():
                section.height = dp(112) if language == code else 0
                section.opacity = 1 if language == code else 0
                section.disabled = language != code
        if hasattr(self, 'ingredient_search') and self.ingredient_search.text.strip():
            self._schedule_ingredient_search()
