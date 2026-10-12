import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
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
    from kivy.core.window import Window
    from kivy.metrics import dp
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.spinner import Spinner
    from cooking_planner.app import CookingPlannerApp
    from cooking_planner.overview.panel import OverviewPanel
    from cooking_planner.plans.week import WeekPlanner
    from cooking_planner.recipes.admin import AdminPanel
    from cooking_planner.recipes.ingredient_admin import IngredientAdminPanel
    from cooking_planner.shopping.draft import ShoppingDraft, item_key
    from cooking_planner.shopping.panel import ShoppingPanel
    from cooking_planner.ui.theme import (GOLD, PANEL_LIGHT, HoverSurface, _mouse_moved,
                                          box, button, tab_button, set_tab_active)
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

    def test_hover_feedback_follows_pointer_and_active_state(self):
        holder = box()
        control = tab_button('Explore', lambda: None, active=True)
        holder.add_widget(control)
        Window.add_widget(holder)
        try:
            holder.do_layout()
            _mouse_moved(Window, control.to_window(*control.center))
            self.assertTrue(control._hovered)
            self.assertEqual(GOLD, control._base_background)
            set_tab_active(control, 'Explore', False)
            self.assertEqual(PANEL_LIGHT, control._base_background)
            control.disabled = True
            self.assertFalse(control._hovered)
            control.disabled = False
            _mouse_moved(Window, (-1, -1))
            self.assertFalse(control._hovered)
        finally:
            Window.remove_widget(holder)

    def test_main_tabs_have_hovering_surfaces_and_controls_keep_hand_cursor(self):
        for tab in ('overview', 'explore', 'week', 'shopping'):
            self.app.show_tab(tab)
            self.assertTrue(any(isinstance(widget, HoverSurface) for widget in self.app.content.walk()), tab)

        holder = box()
        card = box(False, color=PANEL_LIGHT, hover=True, size_hint=(None, None), size=(300, 80))
        control = button('Open', lambda: None)
        card.add_widget(control)
        holder.add_widget(card)
        Window.add_widget(holder)
        try:
            holder.do_layout()
            card.do_layout()
            with patch('cooking_planner.ui.theme._cursor', 'arrow'), patch.object(Window, 'set_system_cursor') as cursor:
                _mouse_moved(Window, control.to_window(*control.center))
                self.assertTrue(card._hovered)
                self.assertTrue(control._hovered)
                cursor.assert_called_with('hand')
            _mouse_moved(Window, (-1, -1))
            self.assertFalse(card._hovered)
        finally:
            Window.remove_widget(holder)

    def test_catalog_notes_only_in_overview_and_recipe_pages_are_visible(self):
        notes = [widget for widget in self.app.root_view.walk()
                 if isinstance(widget, Button) and widget.text == 'About this catalog']
        self.assertEqual(1, len(notes))
        self.app.recipes = []
        for index in range(17):
            recipe = deepcopy(self.recipe)
            recipe['id'] = f'recipe-{index:02d}'
            recipe['name'] = f'Recipe {index:02d}'
            self.app.recipes.append(recipe)
        self.app.show_tab('explore')
        browser = self.app.browser
        self.assertEqual([], [widget for widget in self.app.header.walk()
                              if isinstance(widget, Button) and widget.text == 'About this catalog'])
        self.assertEqual('Recipe pages', browser.page_label.parent.children[-1].text)
        self.assertEqual('Page 1 of 2', browser.page_label.text)
        self.assertTrue(browser.previous_button.disabled)
        self.assertFalse(browser.next_button.disabled)
        browser.next_button.dispatch('on_release', None)
        self.assertEqual('Page 2 of 2', browser.page_label.text)
        self.assertFalse(browser.previous_button.disabled)
        self.assertTrue(browser.next_button.disabled)
        self.assertEqual(1, len(browser.rows.children))

    def test_recipe_tab_shows_each_instruction_as_a_separate_card(self):
        self.recipe['instructions'] = [
            {'step': 1, 'text': 'Prepare the carrots.', 'ingredientIds': ['karotte']},
            {'step': 2, 'text': 'Cook until tender.', 'ingredientIds': []},
        ]
        self.app.show_tab('explore')
        browser = self.app.browser
        browser._show_detail_tab('recipe')
        self.assertEqual(3, len(browser.detail_body.children))
        self.assertEqual('Step 1', browser.detail_body.children[-2].children[-1].text)
        self.assertEqual('Step 2', browser.detail_body.children[-3].children[-1].text)

    def test_recipe_photo_opens_window_sized_gallery(self):
        self.app.show_tab('explore')
        photo = Path(__file__).resolve().parents[2] / 'data' / 'recipe_images' / self.recipe['id'] / 'image_01.png'
        self.assertTrue(photo.is_file())
        popup = self.app.browser._open_image(self.recipe,
                                              [(f"recipe_images/{self.recipe['id']}/image_01.png", photo)], 0)
        self.assertEqual([1, 1], popup.size_hint)
        self.assertIsNotNone(popup.parent)
        popup.dismiss()

    def test_admin_switches_between_recipe_and_ingredient_catalogs(self):
        self.app.tab = 'admin'
        self.app._render_tab()
        with patch.object(self.app, 'list_admin_ingredients',
                          side_effect=lambda query, done: done([])):
            self.app.show_ingredient_admin()
            self.assertIsInstance(self.app.admin_panel, IngredientAdminPanel)
            self.app.show_recipe_admin()
        self.assertIsInstance(self.app.admin_panel, AdminPanel)

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

    def test_overview_reflows_and_week_days_span_the_row(self):
        overview = OverviewPanel([self.recipe], [], {}, 'en', lambda _: None, lambda: None)
        week = WeekPlanner(self.app.week_start, [], 'en', lambda _: None,
                           lambda: None, lambda *_: None, lambda _: None)
        for width, overview_cols in ((dp(400), 1), (dp(650), 2), (dp(950), 3)):
            overview.modules.width = width
            week.scroll.width = width
            self.assertEqual(overview_cols, overview.modules.cols)
            self.assertEqual(7, len(week.days.children))
            self.assertTrue(all(day.orientation == 'horizontal' for day in week.days.children))
            self.assertTrue(all(len(day.children) == 4 for day in week.days.children))

    def test_shopping_dialog_adds_multiple_items_without_reopening(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        dismissed = []
        dialog = SimpleNamespace(open=lambda: None, dismiss=lambda: dismissed.append(True))
        with patch('cooking_planner.shopping.panel.styled_popup', return_value=dialog) as popup:
            panel.add_item()
        body = popup.call_args.args[1]
        form = body.children[1].children[0]
        fields = [child for widget in form.children for child in
                  ([widget] if isinstance(widget, TextInput) else widget.children)
                  if isinstance(child, TextInput)]
        name = next(widget for widget in fields if widget.hint_text == 'Item name')
        amount = next(widget for widget in fields if widget.hint_text == 'Quantity')
        unit = next(child for widget in form.children for child in widget.children
                    if isinstance(child, Spinner))
        price = next(widget for widget in fields if widget.hint_text == 'Price (€), optional')
        actions = next(widget for widget in body.children if any(isinstance(child, Button)
                                                                 for child in widget.children))
        more = next(widget for widget in actions.children if widget.text == 'Add another')
        done = next(widget for widget in actions.children if widget.text == 'Add item')
        name.text, amount.text, unit.text, price.text = 'Milk', '2', 'l', '3,50'
        more.dispatch('on_release', None)
        self.assertEqual('', name.text)
        self.assertEqual('', price.text)
        self.assertEqual(1, len(panel.items))
        self.assertEqual('3.50', str(draft.price_for(panel.start, item_key(panel.items[0]))))
        self.assertFalse(dismissed)
        name.text, amount.text, unit.text = 'Eggs', '6', 'pcs'
        done.dispatch('on_release', None)
        self.assertEqual({'Milk', 'Eggs'}, {item['name'] for item in panel.items})
        self.assertEqual([True], dismissed)

    def test_shopping_dialog_can_select_saved_ingredient(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        searches = []
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None,
                              lambda locale, query, done:
                                  (searches.append((locale, query)), done([{'id': 'karotte', 'name': 'Carrot'}])))
        dialog = SimpleNamespace(open=lambda: None, dismiss=lambda: None)
        with patch('cooking_planner.shopping.panel.styled_popup', return_value=dialog) as popup:
            panel.add_item()
        body = popup.call_args.args[1]
        form = body.children[1].children[0]
        name = next(widget for widget in form.children if isinstance(widget, TextInput)
                    and widget.hint_text == 'Item name')
        suggestions = next(widget for widget in form.children if widget.height == 0
                           and hasattr(widget, 'children'))
        with patch('cooking_planner.shopping.panel.Clock.schedule_once',
                   side_effect=lambda callback, delay:
                       (callback(), SimpleNamespace(cancel=lambda: None))[1]):
            name.text = 'carr'
        self.assertEqual([('en', 'carr')], searches)
        suggestions.children[0].dispatch('on_release', None)
        done = next(widget for widget in body.children[0].children if widget.text == 'Add item')
        done.dispatch('on_release', None)
        self.assertEqual('karotte', panel.items[0]['ingredientId'])

    def test_shopping_items_have_aligned_fields_and_completed_section(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        draft.add_custom(start, 'Rice', '100', 'g')
        draft.add_custom(start, 'Olive oil', '2', 'l')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        rice = panel.rows.children[0]
        self.assertEqual(['[ ]', 'Rice', '100', 'g', 'Set price', '×'],
                         [widget.text for widget in reversed(rice.children) if hasattr(widget, 'text')])
        self.assertEqual('left', rice.children[-2].halign)
        self.assertIsNotNone(rice.children[-2].text_size)
        rice.width = dp(1000)
        self.assertEqual(dp(240), rice.children[-2].width)
        rice.width = dp(390)
        self.assertEqual(dp(80), rice.children[-2].width)
        self.assertEqual('To buy', panel.rows.children[-1].children[-1].text)
        panel.toggle(item_key(next(item for item in panel.items if item['name'] == 'Rice')))
        completed = panel.rows.children[0]
        self.assertEqual(['[x]', 'Rice', '100', 'g', 'Set price', '×'],
                         [widget.text for widget in reversed(completed.children) if hasattr(widget, 'text')])
        self.assertEqual('Completed', panel.rows.children[1].children[-1].text)
        self.assertEqual('1 / 2 items to buy', panel.summary.text)
        panel.scroll.height = dp(120)
        self.assertTrue(panel.compact_list)
        self.assertEqual(2, len(panel.rows.children))
        self.assertEqual('[x]', panel.rows.children[0].children[-1].text)

    def test_shopping_row_price_updates_saved_draft_and_partial_total(self):
        draft = ShoppingDraft(Path(self.temp.name) / 'shopping.json')
        start = self.app.week_start.isoformat()
        draft.add_custom(start, 'Rice', '100', 'g')
        draft.add_custom(start, 'Milk', '2', 'l')
        panel = ShoppingPanel([], [], draft, 'en', self.app.week_start, lambda _: None)
        rice = next(item for item in panel.items if item['name'] == 'Rice')
        def edit_price(value):
            dialog = SimpleNamespace(open=lambda: None, dismiss=lambda: None)
            with patch('cooking_planner.shopping.panel.styled_popup', return_value=dialog) as popup:
                panel.edit_price(rice)
            body = popup.call_args.args[1]
            def descendants(widget):
                yield widget
                for child in widget.children:
                    yield from descendants(child)
            widgets = list(descendants(body))
            price = next(widget for widget in widgets if isinstance(widget, TextInput))
            price.text = value
            save = next(widget for widget in widgets if getattr(widget, 'text', '') == 'Save price')
            save.dispatch('on_release', None)
            return widgets

        edit_price('2,75')
        self.assertEqual('2.75', str(draft.reference_price_for(item_key(rice))[0]))
        self.assertEqual('100', str(draft.reference_price_for(item_key(rice))[1]))
        self.assertEqual('1/2 priced · €2.75', panel.price_summary.text)
        with patch('cooking_planner.shopping.panel.Clipboard.copy') as copy:
            panel.copy()
        self.assertIn('100 g Rice · €2.75', copy.call_args.args[0])
        widgets = edit_price('2.755')
        self.assertEqual('2.75', str(draft.reference_price_for(item_key(rice))[0]))
        self.assertTrue(any('valid euro price' in getattr(widget, 'text', '') for widget in widgets))
        edit_price('')
        self.assertIsNone(draft.price_for(start, item_key(rice), rice['amount']))
        self.assertEqual('0/2 priced · €0.00', panel.price_summary.text)

    def test_meal_selection_stays_open_for_multiple_choices(self):
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
        meal = body.children[1].children[0].children[0]
        meal.dispatch('on_release', None)
        self.assertEqual([], dismissed)
        self.assertEqual({'9'}, draft.selected_plan_ids(start, [plan]))
        self.assertEqual('1 meal selected', panel.meal_summary.text)
        self.assertTrue(panel.items)
        done = body.children[0].children[0]
        done.dispatch('on_release', None)
        self.assertEqual([True], dismissed)

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

if __name__ == '__main__':
    unittest.main()
