import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
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
    from kivy.metrics import dp
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from cooking_planner.app import CookingPlannerApp
    from cooking_planner.overview.panel import OverviewPanel
    from cooking_planner.plans.week import WeekPlanner
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
        self.assertFalse(browser.filters_open)
        browser.toggle_filters()
        self.assertTrue(browser.filters_open)
        self.assertIsNotNone(browser.filter_dialog.parent)
        browser.toggle_filters()
        self.assertFalse(browser.filters_open)
        self.assertIs(self.app.admin_button.parent, self.app.root_view.children[0])
        self.assertIs(self.app.admin_button, self.app.root_view.children[0].children[0])
        self.assertEqual([self.recipe], browser._filtered())
        browser.filters['category'][0].text = 'Missing category'
        self.assertEqual('Filters (1)', browser.filter_toggle.text)
        self.assertEqual([], browser._filtered())
        browser.clear_filters()
        self.assertEqual('Filters', browser.filter_toggle.text)
        browser.search.text = 'no matching dish'
        browser._filter_changed()
        self.assertEqual([], browser._filtered())
        browser.clear_filters()
        browser.select(self.recipe)
        browser._show_detail_tab('ingredients')
        self.assertTrue(browser.detail_tabs['ingredients'].bold)
        browser._show_detail_tab('recipe')
        self.assertTrue(browser.detail_tabs['recipe'].bold)
        self.assertEqual(self.recipe['id'], self.app.selected_id)
        self.app.show_tab('week')
        self.app.show_tab('shopping')
        self.app.show_tab('overview')
        self.assertEqual('overview', self.app.tab)

    def test_saved_plan_opens_its_week_and_drives_shopping(self):
        day = self.app.week_start + timedelta(days=8)
        self.app.show_tab('explore')
        with patch.object(self.app, '_submit', side_effect=lambda work, success: success({'id': 7})), \
             patch.object(self.app, 'refresh') as refresh:
            self.app.save_plan(day, 'DINNER', self.recipe['id'], 3)
        self.assertEqual('week', self.app.tab)
        self.assertEqual(day - timedelta(days=day.weekday()), self.app.week_start)
        refresh.assert_called_once()
        plan = {'id': 7, 'date': day.isoformat(), 'mealType': 'DINNER',
                'recipeId': self.recipe['id'], 'recipeTitle': self.recipe['name'], 'servings': 3}
        self.app._loaded((['en'], [self.recipe], {'countryCount': 1}, [plan]), self.app.generation)
        shopping = self.app.shopping_draft.items(self.app.week_start.isoformat(),
                                                 self.app.plans, self.app.recipes)
        self.assertEqual({str(item['ingredientId']) for item in self.recipe['ingredients']},
                         {item['ingredientId'] for item in shopping})
        first = self.recipe['ingredients'][0]
        self.assertEqual(first['amount'] * 3,
                         next(item['amount'] for item in shopping
                              if item['ingredientId'] == first['ingredientId']))

    def test_shopping_checks_and_scale_persistence(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        draft.add_custom(start, 'Rice', '100', 'g')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        key = item_key(panel.items[0])
        panel.toggle(key)
        self.assertIn(key, draft.week(start)['checked'])
        self.assertTrue(panel.rows.children[0].children[-1].text.startswith('[x]'))
        panel.reset()
        self.assertTrue(panel.rows.children[0].children[-1].text.startswith('[ ]'))
        with patch('cooking_planner.shopping.panel.Clipboard.copy') as copy:
            panel.copy()
        copy.assert_called_once_with('100 g Rice')
        self.assertFalse(draft.week(start)['checked'])
        self.assertEqual(dp(45), panel.actions.height)
        panel.toggle_actions()
        self.assertEqual(dp(90), panel.actions.height)
        self.assertFalse(panel.more_row.disabled)
        panel.toggle_actions()
        self.assertEqual(dp(45), panel.actions.height)
        self.assertTrue(panel.more_row.disabled)
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

    def test_overview_and_week_reflow_when_resized(self):
        overview = OverviewPanel([self.recipe], [], {}, 'en', lambda _: None, lambda: None)
        week = WeekPlanner(self.app.week_start, [], 'en', lambda _: None,
                           lambda: None, lambda *_: None, lambda _: None)
        for width, overview_cols, week_cols in ((dp(400), 1, 1),
                                                 (dp(650), 2, 2),
                                                 (dp(950), 3, 3)):
            overview.modules.width = width
            week.scroll.width = width
            self.assertEqual(overview_cols, overview.modules.cols)
            self.assertEqual(week_cols, week.days.cols)

    def test_shopping_dialog_adds_multiple_items_without_reopening(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        dismissed = []
        dialog = SimpleNamespace(open=lambda: None, dismiss=lambda: dismissed.append(True))
        with patch('cooking_planner.shopping.panel.styled_popup', return_value=dialog) as popup:
            panel.add_item()
        body = popup.call_args.args[1]
        fields = [widget for widget in body.children if isinstance(widget, TextInput)]
        name = next(widget for widget in fields if widget.hint_text == 'Item name')
        amount = next(widget for widget in fields if widget.hint_text == 'Quantity')
        unit = next(widget for widget in fields if widget.hint_text == 'Unit')
        actions = next(widget for widget in body.children if any(isinstance(child, Button)
                                                                 for child in widget.children))
        more = next(widget for widget in actions.children if widget.text == 'Add another')
        done = next(widget for widget in actions.children if widget.text == 'Add item')
        name.text, amount.text, unit.text = 'Milk', '2', 'l'
        more.dispatch('on_release', None)
        self.assertEqual('', name.text)
        self.assertEqual(1, len(panel.items))
        self.assertFalse(dismissed)
        name.text, amount.text, unit.text = 'Eggs', '6', 'pcs'
        done.dispatch('on_release', None)
        self.assertEqual({'Milk', 'Eggs'}, {item['name'] for item in panel.items})
        self.assertEqual([True], dismissed)

    def test_shopping_items_have_aligned_fields_and_completed_section(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        draft.add_custom(start, 'Rice', '100', 'g')
        draft.add_custom(start, 'Olive oil', '2', 'l')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        rice = panel.rows.children[0]
        self.assertEqual(['[ ]', 'Rice', '100', 'g', '×'],
                         [widget.text for widget in reversed(rice.children)])
        self.assertEqual('To buy', panel.rows.children[-1].children[-1].text)
        panel.toggle(item_key(next(item for item in panel.items if item['name'] == 'Rice')))
        completed = panel.rows.children[0]
        self.assertEqual(['[x]', 'Rice', '100', 'g', '×'],
                         [widget.text for widget in reversed(completed.children)])
        self.assertEqual('Completed', panel.rows.children[1].children[-1].text)
        self.assertEqual('1 / 2 items to buy', panel.summary.text)
        panel.scroll.height = dp(120)
        self.assertTrue(panel.compact_list)
        self.assertEqual(2, len(panel.rows.children))
        self.assertEqual('[x]', panel.rows.children[0].children[-1].text)

    def test_meal_selection_closes_after_adding_to_shopping(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        plan = {'id': 9, 'date': start, 'recipeId': self.recipe['id'],
                'recipeTitle': self.recipe['name'], 'servings': 2}
        draft.clear(start, [plan])
        panel = ShoppingPanel([plan], [self.recipe], draft, 'en', self.app.week_start,
                              lambda _: None)
        self.assertEqual('0 meals selected', panel.meal_summary.text)
        dismissed = []
        dialog = SimpleNamespace(open=lambda: None, dismiss=lambda: dismissed.append(True))
        with patch('cooking_planner.shopping.panel.styled_popup', return_value=dialog) as popup:
            panel.choose_meals()
        body = popup.call_args.args[1]
        meal = body.children[0].children[0].children[0]
        meal.dispatch('on_release', None)
        self.assertEqual([True], dismissed)
        self.assertEqual({'9'}, draft.selected_plan_ids(start, [plan]))
        self.assertEqual('1 meal selected', panel.meal_summary.text)
        self.assertTrue(panel.items)

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
