import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_FILELOG', '1')

HAS_DISPLAY = sys.platform != 'linux' or bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
try:
    if not HAS_DISPLAY:
        raise ImportError('No display')
    from kivy.clock import Clock
    from kivy.core.window import Window
    from cooking_planner.app import CookingPlannerApp
    from cooking_planner.recipes.admin import AdminPanel
    from cooking_planner.shopping.draft import ShoppingDraft, item_key
    from cooking_planner.shopping.panel import ShoppingPanel
except ImportError:
    HAS_KIVY = False
else:
    HAS_KIVY = True


def sample_recipe():
    source = json.loads((Path(__file__).resolve().parents[2] / 'data/recipes_en.json').read_text())['recipes'][0]
    return {
        'id': source['id'], 'name': source['name'], 'country': source['country'] or '',
        'region': source['region'] or '', 'continent': source['continent'] or '',
        'categoryLabel': source['category_label'], 'dietTypeLabel': source['diet_type_label'],
        'difficultyLabel': source['difficulty_label'], 'dataSourceLabel': source['data_source_label'],
        'prepMinutes': source['prep_minutes'], 'cookMinutes': source['cook_minutes'],
        'totalMinutes': source['total_minutes'],
        'ingredients': [{'name': item['name'], 'amount': item['amount'], 'unit': item['unit'],
                         'ingredientId': item['ingredient_id']} for item in source['ingredients']],
    }


@unittest.skipUnless(HAS_KIVY, 'Kivy and a desktop display are required')
class UiFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = CookingPlannerApp(object(), config_path=Path(self.temp.name) / 'client.cfg')
        self.app.build()
        recipe = sample_recipe()
        self.app._loaded((['en'], [recipe], {'countryCount': 1, 'dataset': 'Sample'}, []),
                         self.app.generation)
        self.recipe = recipe

    def tearDown(self):
        self.app.worker.shutdown(wait=True, cancel_futures=True)
        self.temp.cleanup()

    def test_browse_filter_selection_and_language_state(self):
        self.app.show_tab('explore')
        browser = self.app.browser
        self.assertIs(browser.search.parent.parent, browser.root.children[1])
        self.assertEqual([self.recipe], browser._filtered())
        browser.search.text = 'no matching dish'
        browser._filter_changed()
        self.assertEqual([], browser._filtered())
        browser.clear_filters()
        browser.select(self.recipe)
        self.assertEqual(self.recipe['id'], self.app.selected_id)
        self.app.show_tab('week')
        self.app.show_tab('shopping')
        self.app.show_tab('overview')
        self.assertEqual('overview', self.app.tab)

    def test_shopping_checks_and_scale_persistence(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        draft.add_custom(start, 'Rice', '100', 'g')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None, lambda: None)
        key = item_key(panel.items[0])
        panel.toggle(key)
        self.assertIn(key, draft.week(start)['checked'])
        panel.reset()
        with patch('cooking_planner.shopping.panel.Clipboard.copy') as copy:
            panel.copy()
        copy.assert_called_once_with('100 g Rice')
        self.assertFalse(draft.week(start)['checked'])
        self.app.change_scale(2.0)
        self.assertIn('scale = 2.0', (Path(self.temp.name) / 'client.cfg').read_text())
        fake_window = SimpleNamespace(fullscreen=False)
        with patch('cooking_planner.app.Window', fake_window):
            self.app.toggle_window()
            self.assertIs(True, fake_window.fullscreen)
            self.assertEqual('Windowed', self.app.window_button.text)
            self.app.toggle_window()
            self.assertIs(False, fake_window.fullscreen)
            self.assertEqual('Fullscreen', self.app.window_button.text)

    def test_admin_requires_a_choice_for_each_language(self):
        saved = []
        messages = []
        panel = AdminPanel([], ('en', 'de'), 'en', lambda _: None,
                           lambda *args: saved.append(args), lambda _: None, lambda: None,
                           messages.append)
        panel.new()
        panel.id_input.text = 'new-test-dish'
        panel.locale_inputs['en']['name'].text = 'New test dish'
        panel.ingredient_rows[0]['names']['en'].text = 'Rice'
        panel.save()
        self.assertFalse(saved)
        self.assertIn('DE:', messages[-1])
        panel.locale_choices['de'].text = 'Omit intentionally'
        panel.save()
        self.assertEqual('new-test-dish', saved[0][0])
        self.assertIsNone(saved[0][2]['de'])
        self.assertEqual('Rice', saved[0][2]['en']['ingredients'][0]['name'])
        self.assertEqual('user_entry', saved[0][2]['en']['data_source'])
        self.assertEqual('User entry', saved[0][2]['en']['data_source_label'])


@unittest.skipUnless(HAS_KIVY, 'Kivy and a desktop display are required')
class AdminEditorTest(unittest.TestCase):
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
        self.assertTrue(panel.page_tabs['details'].text.startswith('● '))
        panel._show_page('recipe')
        self.assertIs(panel.recipe_page, panel.form.children[0])
        self.assertTrue(panel.page_tabs['recipe'].text.startswith('● '))
        self.assertFalse(panel.page_tabs['details'].text.startswith('● '))
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
            panel.save()
            self.assertEqual(45, saved[0][2]['en']['prep_minutes'])
            self.assertEqual(45, saved[0][2]['de']['prep_minutes'])
            self.assertEqual('Changed English name', saved[0][2]['en']['name'])
            self.assertEqual('Geänderter deutscher Name', saved[0][2]['de']['name'])
            self.assertEqual('Spice', saved[0][2]['en']['ingredients'][-1]['name'])
            self.assertEqual('Gewürz', saved[0][2]['de']['ingredients'][-1]['name'])
            self.assertEqual(0.5, saved[0][2]['en']['ingredients'][-1]['amount'])
            self.assertEqual(english['suitable_for'], saved[0][2]['en']['suitable_for'])
            panel.reset()
            self.assertEqual(english['name'], panel.locale_inputs['en']['name'].text)
            self.assertEqual(english['prep_minutes'], int(panel.shared_inputs['prep_minutes'].text))
            self.assertEqual(len(english['ingredients']), len(panel.ingredient_rows))
        finally:
            Window.remove_widget(panel.root)


if __name__ == '__main__':
    unittest.main()
