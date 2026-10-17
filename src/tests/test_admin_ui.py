"""Recipe and ingredient administration UI behavior."""

import json
import base64
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
os.environ.setdefault('KIVY_NO_FILELOG', '1')

HAS_DISPLAY = sys.platform != 'linux' or bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
try:
    if not HAS_DISPLAY:
        raise ImportError('No display')
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.metrics import dp
    from kivy_events import release
    from cooking_planner.recipes.AdminPanel import AdminPanel
    from cooking_planner.recipes.IngredientAdminPanel import IngredientAdminPanel
except ImportError:
    HAS_KIVY = False
else:
    HAS_KIVY = True


@unittest.skipUnless(HAS_KIVY, 'Kivy and a desktop display are required')
class AdminEditorTest(unittest.TestCase):
    def test_ingredient_catalog_can_search_edit_and_reset_translations(self):
        saved = []
        searches = []
        panel = IngredientAdminPanel(('en', 'de'), 'en', lambda: None,
                                     lambda query, callback: searches.append((query, callback)),
                                     lambda ingredient_id, names: saved.append((ingredient_id, names)),
                                     lambda _: None, lambda _: None)
        panel.search.text = 'carr'
        panel._show_results([{'id': 'karotte', 'translations': {'en': 'Carrot', 'de': 'Karotte'}}],
                            panel.generation)
        release(panel.results.children[0])
        panel.names['en'].text = 'Garden carrot'
        panel.save()
        self.assertEqual(('karotte', {'en': 'Garden carrot', 'de': 'Karotte'}), saved[-1])
        panel.reset()
        self.assertEqual('Carrot', panel.names['en'].text)
        panel.new()
        panel.id_input.text = 'new-spice'
        panel.names['de'].text = 'Gewürz'
        panel.save()
        self.assertEqual(('new-spice', {'en': '', 'de': 'Gewürz'}), saved[-1])

    def test_ingredient_catalog_pages_all_search_results(self):
        panel = IngredientAdminPanel(('en',), 'en', lambda: None,
                                     lambda *_: None, lambda *_: None,
                                     lambda *_: None, lambda *_: None)
        header_scroll = panel.root.children[-1]
        header_scroll.width = dp(400)
        self.assertGreaterEqual(header_scroll.children[0].width, dp(510))
        panel.horizontal.width = dp(400)
        self.assertFalse(panel.list_button.disabled)
        rows = [{'id': f'ingredient-{index:03d}',
                 'translations': {'en': f'Ingredient {index:03d}'}} for index in range(101)]
        panel._show_results(rows, panel.generation)
        self.assertEqual('Page 1 of 3', panel.page_label.text)
        self.assertEqual(41, len(panel.results.children))
        release(panel.next_button)
        release(panel.next_button)
        self.assertEqual('Page 3 of 3', panel.page_label.text)
        self.assertTrue(panel.next_button.disabled)
        self.assertEqual(22, len(panel.results.children))
        release(panel.results.children[0])
        self.assertEqual('ingredient-100', panel.selected['id'])
        self.assertEqual(1, panel.horizontal.scroll_x)
        release(panel.list_button)
        self.assertEqual(0, panel.horizontal.scroll_x)
        panel.search.text = 'Ingredient 100'
        panel._show_results(rows[-1:], panel.generation)
        self.assertEqual('Page 1 of 1', panel.page_label.text)

    def test_ingredient_catalog_edits_reusable_prices_by_unit(self):
        saved = []
        panel = IngredientAdminPanel(('en',), 'en', lambda: None,
                                     lambda *_: None, lambda *_: None, lambda *_: None,
                                     lambda *_: None,
                                     reference_prices={'rice:g': {'price': '1.80', 'basisQuantity': 100}},
                                     on_save_price=lambda *args: saved.append(args))
        panel.select({'id': 'rice', 'translations': {'en': 'Rice'}})
        panel.show_editor_tab('pricing')
        self.assertTrue(panel.pricing_tab.bold)
        self.assertEqual('1.80', panel.price_input.text)
        self.assertEqual('100 g', panel.price_basis.text)
        panel.price_input.text = '2,50'
        panel.price_basis.text = '1 kg'
        panel.save_price()
        self.assertEqual(('rice', 'g', '2.50', 1000), saved[-1])
        panel.price_unit.text = 'ml'
        self.assertEqual('', panel.price_input.text)
        panel.price_input.text = '2.555'
        panel.save_price()
        self.assertEqual(1, len(saved))
        panel.price_input.text = '1.10'
        panel.save_price()
        self.assertEqual(('rice', 'ml', '1.10', 100), saved[-1])
        panel.update_prices({'rice:g': {'price': '2.50', 'basisQuantity': 1000},
                             'rice:ml': {'price': '1.10', 'basisQuantity': 100}})
        self.assertEqual('1.10', panel.price_input.text)
        panel.price_input.text = ''
        panel.save_price()
        self.assertEqual(('rice', 'ml', '', 100), saved[-1])
        panel.update_prices({'milk:ml': {'price': '2.20', 'basisQuantity': 100}})
        panel.select({'id': 'milk', 'translations': {'en': 'Milk'}})
        self.assertEqual('pricing', panel.editor_tab)
        self.assertEqual('ml', panel.price_unit.text)
        self.assertEqual('2.20', panel.price_input.text)
        panel.new()
        self.assertEqual('details', panel.editor_tab)
        self.assertTrue(panel.pricing_tab.disabled)

    def test_ingredient_picker_opens_with_catalog_choices_without_typing(self):
        catalog = [{'id': 'karotte', 'translations': {'en': 'Carrot', 'de': 'Karotte'}}]
        panel = AdminPanel([], ('en', 'de'), 'en', lambda _: None, lambda *args: None,
                           lambda _: None, lambda: None, lambda _: None,
                           ingredient_catalog=catalog)
        panel.new()
        panel._show_page('ingredients')
        popup = panel.add_ingredient()
        self.assertTrue(any(getattr(child, 'text', '') == 'Carrot'
                            for child in popup.content.children[1].children[0].children))
        panel._select_ingredient(catalog[0])
        popup.dismiss()
        self.assertEqual('karotte', panel.ingredient_rows[0]['shared']['ingredient_id'].text)
        self.assertEqual('Carrot', panel.ingredient_rows[0]['names']['en'].text)
        self.assertEqual('Karotte', panel.ingredient_rows[0]['names']['de'].text)

    def test_status_tab_is_available_without_a_selected_recipe(self):
        panel = AdminPanel([], ('en',), 'en', lambda _: None, lambda *args: None,
                           lambda _: None, lambda: None, lambda _: None)
        panel._show_page('status')
        panel.set_status('Backend ready')
        self.assertIn(panel.status_page, panel.form.children)
        self.assertEqual('Backend ready', panel.status_text.text)

    def test_catalog_choices_change_labels_without_losing_codes(self):
        data = Path(__file__).resolve().parents[2] / 'data'
        english = json.loads((data / 'recipes_en.json').read_text())['recipes'][0]
        german = json.loads((data / 'recipes_de.json').read_text())['recipes'][0]
        options = {
            'en': {'category': [{'value': 'main', 'label': 'Main'},
                                {'value': 'soup', 'label': 'Soup'}]},
            'de': {'category': [{'value': 'main', 'label': 'Hauptgericht'},
                                {'value': 'soup', 'label': 'Suppe'}]},
        }
        saved = []
        catalog = [{'id': item['ingredient_id'], 'translations': {
                    'en': item['name'], 'de': next((other['name'] for other in german['ingredients']
                    if other['ingredient_id'] == item['ingredient_id']), item['name'])}}
                   for item in english['ingredients']]
        panel = AdminPanel([], ('de', 'en'), 'en', lambda _: None, lambda *args: saved.append(args),
                           lambda _: None, lambda: None, lambda _: None, options,
                           ingredient_catalog=catalog)
        panel.show_recipe({'id': english['id'], 'translations': {'en': english, 'de': german}})
        self.assertIn(panel.details, panel.form.children)
        self.assertTrue(panel.page_tabs['details'].bold)
        panel._show_page('recipe')
        self.assertIn(panel.recipe_page, panel.form.children)
        self.assertTrue(panel.page_tabs['recipe'].bold)
        self.assertFalse(panel.page_tabs['details'].bold)
        self.assertEqual(english['name'], panel.recipe_title.text)
        panel.language.text = 'DE'
        self.assertEqual(german['name'], panel.recipe_title.text)
        panel._show_page('details')
        panel.language.text = 'EN'
        category = panel.shared_inputs['category']
        category.text = 'Soup · soup'
        panel.language.text = 'DE'
        self.assertEqual('Suppe · soup', category.text)
        panel._show_page('ingredients')
        self.assertIn(panel.ingredients_page, panel.form.children)
        panel.save()
        self.assertEqual('soup', saved[0][2]['en']['category'])
        self.assertEqual('Soup', saved[0][2]['en']['category_label'])
        self.assertEqual('Suppe', saved[0][2]['de']['category_label'])

    def test_labeled_fields_update_all_languages_and_reset_to_loaded(self):
        data = Path(__file__).resolve().parents[2] / 'data'
        english = json.loads((data / 'recipes_en.json').read_text())['recipes'][0]
        german = json.loads((data / 'recipes_de.json').read_text())['recipes'][0]
        saved = []
        catalog = [{'id': item['ingredient_id'], 'translations': {
                    'en': item['name'], 'de': next((other['name'] for other in german['ingredients']
                    if other['ingredient_id'] == item['ingredient_id']), item['name'])}}
                   for item in english['ingredients']]
        catalog.append({'id': 'test-spice', 'translations': {'en': 'Spice', 'de': 'Gewürz'}})
        panel = AdminPanel([], ('de', 'en'), 'en', lambda _: None, lambda *args: saved.append(args),
                           lambda _: None, lambda: None, lambda _: None,
                           ingredient_catalog=catalog)
        Window.add_widget(panel.root)
        try:
            panel.show_recipe({'id': english['id'], 'translations': {'de': german, 'en': english}})
            Clock.tick()
            Clock.tick()
            self.assertEqual(english['name'], panel.locale_inputs['en']['name'].text)
            self.assertEqual(german['name'], panel.locale_inputs['de']['name'].text)
            panel.shared_inputs['prep_minutes'].text = '45'
            panel.locale_inputs['en']['name'].text = 'Changed English name'
            panel.locale_inputs['de']['name'].text = 'Geänderter deutscher Name'
            panel._select_ingredient(catalog[-1])
            added = panel.ingredient_rows[-1]
            added['shared']['amount'].text = '0.5'
            panel.step_rows[0]['texts']['en'].text = 'Prepare all ingredients.'
            panel.step_rows[0]['texts']['de'].text = 'Alle Zutaten vorbereiten.'
            panel.add_step()
            final_step = panel.step_rows[-1]
            panel._toggle_step_ingredient(final_step, added)
            final_step['texts']['en'].text = 'Add the spice.'
            final_step['texts']['de'].text = 'Das Gewürz zugeben.'
            panel.save()
            self.assertEqual(45, saved[0][2]['en']['prep_minutes'])
            self.assertEqual(45, saved[0][2]['de']['prep_minutes'])
            self.assertEqual('Changed English name', saved[0][2]['en']['name'])
            self.assertEqual('Geänderter deutscher Name', saved[0][2]['de']['name'])
            self.assertEqual('Spice', saved[0][2]['en']['ingredients'][-1]['name'])
            self.assertEqual('Gewürz', saved[0][2]['de']['ingredients'][-1]['name'])
            self.assertEqual(0.5, saved[0][2]['en']['ingredients'][-1]['amount'])
            self.assertEqual(english['suitable_for'], saved[0][2]['en']['suitable_for'])
            self.assertEqual('Prepare all ingredients.', saved[0][2]['en']['instructions']['steps'][0]['text'])
            self.assertEqual('Alle Zutaten vorbereiten.', saved[0][2]['de']['instructions']['steps'][0]['text'])
            self.assertEqual(['test-spice'], saved[0][2]['de']['instructions']['steps'][-1]['ingredient_ids'])
            panel.reset()
            self.assertEqual(english['name'], panel.locale_inputs['en']['name'].text)
            self.assertEqual(english['prep_minutes'], int(panel.shared_inputs['prep_minutes'].text))
            self.assertEqual(len(english['ingredients']), len(panel.ingredient_rows))
            self.assertEqual(len(english['instructions']['steps']), len(panel.step_rows))
        finally:
            Window.remove_widget(panel.root)

    def test_new_recipe_steps_can_be_removed_and_choose_ingredients_by_name(self):
        catalog = [{'id': 'carrot', 'translations': {'en': 'Carrot'}}]
        panel = AdminPanel([], ('en',), 'en', lambda _: None, lambda *args: None,
                           lambda _: None, lambda: None, lambda _: None,
                           ingredient_catalog=catalog)
        panel.new()
        panel._select_ingredient(catalog[0])
        ingredient = panel.ingredient_rows[0]
        ingredient['shared']['amount'].text = '2'
        panel.add_step()
        first = panel.step_rows[0]
        self.assertTrue(any('Carrot · 2 g' in choice.text for choice in first['choices'].children))
        panel._toggle_step_ingredient(first, ingredient)
        self.assertEqual([ingredient], first['selected'])
        panel.add_step()
        self.assertEqual(1, panel.active_step)
        panel._remove_step(panel.step_rows[-1])
        self.assertEqual([first], panel.step_rows)
        self.assertIs(first['card'], panel.steps_container.children[0])
        panel._remove_step(first)
        self.assertEqual([], panel.step_rows)

    def test_recipe_images_use_picker_slots_and_country_specific_id(self):
        catalog = [{'id': 'apple', 'translations': {'en': 'Apple'}}]
        saved = []
        options = {'en': {'country_code': [{'value': 'at', 'label': 'Austria'}]}}
        panel = AdminPanel([], ('en',), 'en', lambda _: None,
                           lambda *args: saved.append(args), lambda _: None,
                           lambda: None, lambda _: None, options,
                           ingredient_catalog=catalog)
        panel.new()
        panel.locale_inputs['en']['name'].text = 'Apple pie'
        panel.shared_inputs['country_code'].text = 'Austria · at'
        panel._select_ingredient(catalog[0])
        photo = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==')
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / 'first.png'
            second = Path(temporary) / 'second.png'
            first.write_bytes(photo)
            second.write_bytes(photo)
            self.assertTrue(panel.image_editor.select(1, first))
            self.assertFalse(panel.image_editor.select(2, second))
            self.assertIn('already selected', panel.image_editor.notice.text)
            panel.save()
        self.assertEqual('at-apple-pie', saved[0][0])
        self.assertIn('Austria', panel.image_editor.context.text)
        self.assertEqual(1, len(saved[0][4]))
        self.assertTrue(saved[0][4][0]['reference'].startswith(
            'recipe_images/at-apple-pie/image_01-'))



if __name__ == '__main__':
    unittest.main()
