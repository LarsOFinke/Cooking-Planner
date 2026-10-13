"""Recipe and ingredient administration UI behavior."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
    from cooking_planner.recipes.admin import AdminPanel
    from cooking_planner.recipes.ingredient_admin import IngredientAdminPanel
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
        panel.results.children[0].dispatch('on_release', None)
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
        panel.next_button.dispatch('on_release', None)
        panel.next_button.dispatch('on_release', None)
        self.assertEqual('Page 3 of 3', panel.page_label.text)
        self.assertTrue(panel.next_button.disabled)
        self.assertEqual(22, len(panel.results.children))
        panel.results.children[0].dispatch('on_release', None)
        self.assertEqual('ingredient-100', panel.selected['id'])
        self.assertEqual(1, panel.horizontal.scroll_x)
        panel.list_button.dispatch('on_release', None)
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

    def test_ingredient_search_fills_shared_id_and_localized_names(self):
        searches = []
        panel = AdminPanel([], ('en', 'de'), 'en', lambda _: None, lambda *args: None,
                           lambda _: None, lambda: None, lambda _: None,
                           on_ingredient_search=lambda locale, query, callback:
                               searches.append((locale, query, callback)))
        panel.new()
        panel._show_page('ingredients')
        with patch('cooking_planner.recipes.admin.Clock.schedule_once',
                   side_effect=lambda callback, delay: callback()):
            panel.ingredient_search.text = 'carr'
        self.assertEqual(('en', 'carr'), searches[-1][:2])
        searches[-1][2]([{'id': 'karotte', 'name': 'Carrot',
                          'translations': {'en': 'Carrot', 'de': 'Karotte'}}])
        panel.ingredient_matches.children[0].dispatch('on_release', None)
        self.assertEqual('karotte', panel.ingredient_rows[0]['shared']['ingredient_id'].text)
        self.assertEqual('Carrot', panel.ingredient_rows[0]['names']['en'].text)
        self.assertEqual('Karotte', panel.ingredient_rows[0]['names']['de'].text)

    def test_status_tab_is_available_without_a_selected_recipe(self):
        panel = AdminPanel([], ('en',), 'en', lambda _: None, lambda *args: None,
                           lambda _: None, lambda: None, lambda _: None)
        panel._show_page('status')
        panel.set_status('Backend ready')
        self.assertIs(panel.status_page, panel.form.children[0])
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
        panel = AdminPanel([], ('de', 'en'), 'en', lambda _: None, lambda *args: saved.append(args),
                           lambda _: None, lambda: None, lambda _: None, options)
        panel.show_recipe({'id': english['id'], 'translations': {'en': english, 'de': german}})
        self.assertIs(panel.details, panel.form.children[0])
        self.assertTrue(panel.page_tabs['details'].bold)
        panel._show_page('recipe')
        self.assertIs(panel.recipe_page, panel.form.children[0])
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
        self.assertIs(panel.ingredients_page, panel.form.children[0])
        panel.save()
        self.assertEqual('soup', saved[0][2]['en']['category'])
        self.assertEqual('Soup', saved[0][2]['en']['category_label'])
        self.assertEqual('Suppe', saved[0][2]['de']['category_label'])

    def test_labeled_fields_update_all_languages_and_reset_to_loaded(self):
        data = Path(__file__).resolve().parents[2] / 'data'
        english = json.loads((data / 'recipes_en.json').read_text())['recipes'][0]
        german = json.loads((data / 'recipes_de.json').read_text())['recipes'][0]
        saved = []
        panel = AdminPanel([], ('de', 'en'), 'en', lambda _: None, lambda *args: saved.append(args),
                           lambda _: None, lambda: None, lambda _: None)
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
            panel.add_ingredient()
            added = panel.ingredient_rows[-1]
            added['shared']['ingredient_id'].text = 'test-spice'
            added['shared']['amount'].text = '0.5'
            added['names']['en'].text = 'Spice'
            added['names']['de'].text = 'Gewürz'
            panel.step_rows[0]['texts']['en'].text = 'Prepare all ingredients.'
            panel.step_rows[0]['texts']['de'].text = 'Alle Zutaten vorbereiten.'
            panel.add_step()
            final_step = panel.step_rows[-1]
            final_step['ids'].text = 'test-spice'
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



if __name__ == '__main__':
    unittest.main()
