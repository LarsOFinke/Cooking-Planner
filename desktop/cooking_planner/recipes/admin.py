"""Catalog-backed recipe editor; writes are handled by the backend API."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton

from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import (GOLD, MUTED, PANEL, PANEL_LIGHT, WHITE, box, button,
                                      field, label, set_tab_active, spinner, tab_button)

CHOICES = (
    ('country_code', 'admin_country'), ('region_code', 'admin_region'),
    ('continent_code', 'admin_continent'), ('category', 'category'),
    ('difficulty', 'difficulty'), ('effort', 'effort'),
    ('diet_type', 'diet'), ('data_source', 'admin_data_source_label'),
)
LABELS = {
    'country_code': 'country', 'region_code': 'region', 'continent_code': 'continent',
    'category': 'category_label', 'difficulty': 'difficulty_label',
    'effort': 'effort_label', 'diet_type': 'diet_type_label', 'data_source': 'data_source_label',
}
TIMES = (('prep_minutes', 'admin_prep_minutes'), ('cook_minutes', 'admin_cook_minutes'),
         ('total_minutes', 'admin_total_minutes'))


def new_recipe_template(recipe_id):
    return {
        'id': recipe_id, 'name': '', 'country': '', 'country_code': '', 'region': '', 'continent': '',
        'category': 'main', 'difficulty': 'medium', 'effort': 'medium', 'data_source': 'user_entry',
        'prep_minutes': 0, 'cook_minutes': 0, 'total_minutes': 0, 'diet_type': 'omnivore',
        'suitable_for': ['flexitarian', 'omnivore'],
        'ingredients': [{'name': '', 'ingredient_id': 'ingredient-id', 'amount': 1, 'unit': 'g'}],
        'region_code': '', 'continent_code': '', 'category_label': '', 'difficulty_label': '',
        'effort_label': '', 'diet_type_label': '', 'suitable_for_labels': [],
        'data_source_label': '', 'image_folder': f'recipe_images/{recipe_id}', 'images': [],
    }


def translation_template(recipe):
    translated = deepcopy(recipe)
    for key in ('name', *LABELS.values()):
        translated[key] = ''
    translated['suitable_for_labels'] = []
    for ingredient in translated['ingredients']:
        ingredient['name'] = ''
    return translated


class AdminPanel:
    def __init__(self, records, locales, locale, on_select, on_save, on_delete, on_reload, on_status,
                 options=None):
        self.records, self.locales, self.locale = records, tuple(locales), locale
        self.on_select, self.on_save = on_select, on_save
        self.on_delete, self.on_reload, self.on_status = on_delete, on_reload, on_status
        self.options = options or {}
        self.entry, self.creating, self.page = None, False, 'details'
        self.root = box(spacing=8)
        header = box(False, spacing=8, size_hint_y=None, height=dp(46))
        header.add_widget(label(t(locale, 'admin'), 22, GOLD, 46, True))
        header.add_widget(button(t(locale, 'admin_new'), self.new, 'primary',
                                 size_hint_x=None, width=dp(145)))
        header.add_widget(button(t(locale, 'refresh'), on_reload, size_hint_x=None, width=dp(115)))
        self.root.add_widget(header)
        horizontal = ScrollView(do_scroll_y=False)
        columns = box(False, spacing=8, size_hint_x=None)
        horizontal.bind(width=lambda _, width: setattr(columns, 'width', max(width, dp(780))))
        horizontal.add_widget(columns)
        self.root.add_widget(horizontal)
        left = box(padding=8, spacing=6, color=PANEL, size_hint_x=None, width=dp(235))
        self.search = field(t(locale, 'admin_search'))
        self.search.bind(text=lambda *_: self._render_list())
        left.add_widget(self.search)
        list_scroll = ScrollView(do_scroll_x=False)
        self.list_rows = box(spacing=4, size_hint_y=None)
        self.list_rows.bind(minimum_height=self.list_rows.setter('height'))
        list_scroll.add_widget(self.list_rows)
        left.add_widget(list_scroll)
        columns.add_widget(left)
        right = box(spacing=6)
        self.toolbar = box(False, spacing=7, size_hint_y=None, height=dp(44))
        right.add_widget(self.toolbar)
        editor_scroll = ScrollView(do_scroll_x=False)
        self.form = box(padding=dp(12), color=PANEL, size_hint_y=None)
        self.form.bind(minimum_height=self.form.setter('height'))
        editor_scroll.add_widget(self.form)
        right.add_widget(editor_scroll)
        self.actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
        right.add_widget(self.actions)
        columns.add_widget(right)
        self._render_list()
        self._render_form()

    def _render_list(self):
        self.list_rows.clear_widgets()
        query = self.search.text.casefold().strip()
        matches = [record for record in self.records if query in
                   (record['id'] + ' ' + ' '.join(record['names'].values())).casefold()]
        self.list_rows.add_widget(label(f"{len(matches)} {t(self.locale, 'results')}", 13, MUTED, 28))
        for record in matches[:80]:
            name = record['names'].get(self.locale) or next(iter(record['names'].values()), '')
            self.list_rows.add_widget(button(f"{name}\n{record['id']}",
                                             lambda recipe_id=record['id']: self.on_select(recipe_id), height=62))

    def show_recipe(self, entry):
        self.entry, self.creating = deepcopy(entry), False
        self.page = 'details'
        self._render_form()

    def new(self):
        self.entry, self.creating = None, True
        self.page = 'details'
        self._render_form()

    def reset(self):
        self._render_form()

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
        choices = {item['value']: item['label'] for item in self.options.get(locale, {}).get(key, [])}
        if key == 'data_source':
            choices.setdefault('user_entry', t(locale, 'admin_user_entry'))
        return choices

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
        self.form.clear_widgets()
        self.toolbar.clear_widgets()
        self.actions.clear_widgets()
        self.shared_inputs, self.locale_inputs, self.locale_choices = {}, {}, {}
        self.ingredient_rows = []
        if not self.creating and self.entry is None:
            self.form.add_widget(label(t(self.locale, 'admin_select'), 16, MUTED, 80))
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
                                size_hint_x=None, width=dp(85))
        self.language.bind(text=lambda *_: self._change_language(self.language.text.lower()))
        self.toolbar.add_widget(label(t(self.locale, 'admin_edit_language'), 14, WHITE, 40,
                                      size_hint_x=None, width=dp(125)))
        self.toolbar.add_widget(self.language)
        self.page_titles = {'details': 'admin_details_tab', 'ingredients': 'admin_ingredients',
                            'recipe': 'admin_recipe_tab'}
        self.page_tabs = {}
        for page, title in self.page_titles.items():
            control = tab_button(t(self.locale, title), lambda selected=page: self._show_page(selected),
                                 page == self.page)
            self.page_tabs[page] = control
            self.toolbar.add_widget(control)
        self.details = box(spacing=8, size_hint_y=None)
        self.details.bind(minimum_height=self.details.setter('height'))
        self.ingredients_page = box(spacing=8, size_hint_y=None)
        self.ingredients_page.bind(minimum_height=self.ingredients_page.setter('height'))
        self.recipe_page = box(spacing=10, size_hint_y=None)
        self.recipe_page.bind(minimum_height=self.recipe_page.setter('height'))
        self._heading(self.recipe_page, 'admin_recipe_tab')
        self.recipe_title = label('', 18, WHITE, 42, True)
        self.recipe_page.add_widget(self.recipe_title)
        self.recipe_page.add_widget(label(t(self.locale, 'admin_recipe_future'), 15, MUTED, 70))
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
            toggle = ToggleButton(text=diets.get(value, value), activated=value in selected,
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
        self._heading(self.ingredients_page, 'admin_ingredients')
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
        self._change_language(source)
        self._show_page(self.page)
        self.actions.add_widget(button(t(self.locale, 'admin_create' if self.creating else 'admin_update'),
                                       self.save, 'primary'))
        self.actions.add_widget(button(t(self.locale, 'admin_reset'), self.reset))
        if not self.creating:
            self.actions.add_widget(button(t(self.locale, 'admin_delete'),
                                           lambda: self.on_delete(self.entry['id']), 'danger'))

    def _show_page(self, page):
        self.page = page
        for name, control in self.page_tabs.items():
            set_tab_active(control, t(self.locale, self.page_titles[name]), name == page)
        self.recipe_title.text = (self.locale_inputs[self.edit_locale]['name'].text.strip()
                                  or t(self.locale, 'admin_unnamed_recipe'))
        self.form.clear_widgets()
        self.form.add_widget({'details': self.details, 'ingredients': self.ingredients_page,
                              'recipe': self.recipe_page}[page])

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

    def _shared_values(self):
        values = {}
        for key, title in CHOICES:
            values[key] = self._value(self.shared_inputs[key])
            if not values[key] and key not in ('country_code', 'region_code', 'continent_code'):
                self.on_status(f"{t(self.locale, title)}: {t(self.locale, 'admin_select_option')}")
                return None
        for key, title in TIMES:
            try:
                values[key] = int(self.shared_inputs[key].text.strip())
            except ValueError:
                self.on_status(f"{t(self.locale, title)}: {t(self.locale, 'admin_whole_number')}")
                return None
        values['suitable_for'] = [code for code, widget in self.diet_buttons.items() if widget.activated]
        values['images'] = [line.strip() for line in self.shared_inputs['images'].text.splitlines() if line.strip()]
        return values

    def _ingredients(self):
        if not self.ingredient_rows:
            self.on_status(t(self.locale, 'admin_need_ingredient'))
            return None
        rows = []
        for entry in self.ingredient_rows:
            try:
                amount = Decimal(entry['shared']['amount'].text.strip())
                if not amount.is_finite() or amount <= 0 or amount > 1_000_000_000:
                    raise InvalidOperation
            except InvalidOperation:
                self.on_status(f"{t(self.locale, 'admin_amount')}: {t(self.locale, 'admin_positive_number')}")
                return None
            rows.append((entry, int(amount) if amount == amount.to_integral_value() else float(amount)))
        return rows

    def _label_for(self, locale, key, value):
        options = self._options(key, locale)
        if value in options:
            return options[value]
        document = self.documents[locale]
        label_key = LABELS.get(key)
        if label_key and document.get(key) == value and document.get(label_key):
            return document[label_key]
        return value

    def save(self):
        recipe_id = self.id_input.text.strip()
        source = self.source.text.lower()
        if not recipe_id:
            self.on_status(t(self.locale, 'admin_missing_id'))
            return
        if self.locale_choices[source].text != t(self.locale, 'admin_translate'):
            self.on_status(t(self.locale, 'admin_source_required'))
            return
        for code, choice in self.locale_choices.items():
            if choice.text == t(self.locale, 'admin_choose'):
                self.on_status(f"{code.upper()}: {t(self.locale, 'admin_choose_language')}")
                return
        shared = self._shared_values()
        ingredients = self._ingredients()
        if shared is None or ingredients is None:
            return
        translations = {}
        for code, choice in self.locale_choices.items():
            if choice.text == t(self.locale, 'admin_omit'):
                translations[code] = None
                continue
            row = deepcopy(self.documents[code])
            row.update(shared)
            row['id'] = recipe_id
            row['image_folder'] = f'recipe_images/{recipe_id}'
            row['name'] = self.locale_inputs[code]['name'].text.strip()
            for key, label_key in LABELS.items():
                row[label_key] = self._label_for(code, key, shared[key])
            row['suitable_for_labels'] = [self._label_for(code, 'suitable_for', value)
                                          for value in shared['suitable_for']]
            row['ingredients'] = []
            for entry, amount in ingredients:
                item = deepcopy(entry['original'])
                item.update({'ingredient_id': entry['shared']['ingredient_id'].text.strip(),
                             'amount': amount, 'unit': entry['shared']['unit'].text.strip(),
                             'name': entry['names'][code].text.strip()})
                row['ingredients'].append(item)
            translations[code] = row
        self.on_save(recipe_id, source, translations, self.creating)
