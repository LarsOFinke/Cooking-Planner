import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.pricing import normalize_price
from cooking_planner.shopping.persistence import save_draft
from cooking_planner.shopping.ShoppingDraft import UPCOMING, ShoppingDraft, item_key


class ShoppingDraftTest(unittest.TestCase):
    def test_upcoming_list_includes_future_meals_and_preserves_current_custom_items(self):
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'date': '2026-10-18', 'recipeId': 'dish', 'servings': 2},
                 {'id': 2, 'date': '2026-11-02', 'recipeId': 'dish', 'servings': 1}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.add_custom('2026-10-12', 'Milk', '1', 'l')
            draft.use_upcoming('2026-10-12')
            self.assertEqual({'1', '2'}, draft.selected_plan_ids(UPCOMING, plans))
            self.assertEqual({'Rice', 'Milk'}, {item['name'] for item in draft.items(UPCOMING, plans, recipes)})
            draft.toggle_plan(UPCOMING, 2)
            self.assertEqual({'1'}, ShoppingDraft(path).selected_plan_ids(UPCOMING, plans))

    def test_bought_recipe_status_uses_shared_ingredients_and_recipe_signature(self):
        recipes = [{'id': 'one', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]},
                   {'id': 'two', 'ingredients': [
                       {'ingredientId': 'rice', 'name': 'Rice', 'amount': 50, 'unit': 'g'},
                       {'ingredientId': 'salt', 'name': 'Salt', 'amount': 1, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'one', 'servings': 2},
                 {'id': 2, 'recipeId': 'two', 'servings': 1}]
        draft = ShoppingDraft()
        draft.toggle_checked(UPCOMING, 'rice:g')
        draft.update_bought_plans(UPCOMING, plans, recipes)
        self.assertEqual({'1'}, draft.bought_plan_ids(UPCOMING, plans, recipes))
        draft.toggle_checked(UPCOMING, 'salt:g')
        draft.update_bought_plans(UPCOMING, plans, recipes)
        self.assertEqual({'1', '2'}, draft.bought_plan_ids(UPCOMING, plans, recipes))
        plans[0]['servings'] = 3
        self.assertEqual({'2'}, draft.bought_plan_ids(UPCOMING, plans, recipes))
        recipes[1]['ingredients'].append(
            {'ingredientId': 'pepper', 'name': 'Pepper', 'amount': 1, 'unit': 'g'})
        self.assertEqual(set(), draft.bought_plan_ids(UPCOMING, plans, recipes))

    def test_upcoming_manual_price_does_not_queue_invalid_week_in_sqlite(self):
        draft = ShoppingDraft()
        writes = []
        draft.price_writer = lambda *values: writes.append(values)
        draft.price_clearer = lambda value: writes.append(value)
        draft.add_custom(UPCOMING, 'Milk', '1', 'l', '2.50')
        item = draft.week(UPCOMING)['custom'][0]
        self.assertEqual('2.50', str(draft.price_for(UPCOMING, item_key(item))))
        self.assertEqual([], writes)
        draft.clear(UPCOMING, [])
        self.assertEqual([], writes)

    def test_interrupted_shopping_save_keeps_previous_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            path.write_text('previous contents', encoding='utf-8')
            with patch('cooking_planner.shopping.persistence.os.replace', side_effect=OSError('interrupted')), \
                 self.assertRaises(OSError):
                save_draft(path, {}, [])
            self.assertEqual('previous contents', path.read_text(encoding='utf-8'))
            self.assertEqual([], list(path.parent.glob('shopping.json.*.tmp')))

    def test_add_day_restores_only_selected_days_meals_after_clear(self):
        start = '2026-10-05'
        plans = [{'id': 1, 'date': start}, {'id': 2, 'date': start},
                 {'id': 3, 'date': '2026-10-06'}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.clear(start, plans)
            self.assertEqual(set(), draft.selected_plan_ids(start, plans))
            self.assertEqual(2, draft.add_day(start, plans, start))
            self.assertEqual({'1', '2'}, ShoppingDraft(path).selected_plan_ids(start, plans))
            self.assertEqual(0, draft.add_day(start, plans, '2026-10-07'))

    def test_clear_stays_empty_when_week_plan_changes(self):
        start = '2026-10-05'
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 2}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.add_all(start, plans)
            draft.add_custom(start, 'Milk', '1', 'l')
            draft.clear(start, plans)
            plans.append({'id': 2, 'recipeId': 'dish', 'servings': 1})
            restored = ShoppingDraft(path)
            self.assertEqual([], restored.items(start, plans, recipes))
            self.assertEqual(set(), restored.selected_plan_ids(start, plans))

    def test_explicit_meal_import_restores_its_excluded_ingredients(self):
        start = '2026-10-05'
        plans = [{'id': 1, 'date': start, 'recipeId': 'rice', 'servings': 2},
                 {'id': 2, 'date': '2026-10-06', 'recipeId': 'beans', 'servings': 1}]
        recipes = [{'id': 'rice', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]},
            {'id': 'beans', 'ingredients': [
                {'ingredientId': 'beans', 'name': 'Beans', 'amount': 50, 'unit': 'g'}]}]
        draft = ShoppingDraft()
        draft.week(start)['excluded'] = ['rice:g', 'beans:g']
        self.assertEqual(1, draft.add_day(start, plans, start, recipes))
        self.assertEqual(['Rice'], [item['name'] for item in draft.items(start, plans, recipes)])
        self.assertEqual(['beans:g'], draft.week(start)['excluded'])
        draft.toggle_plan(start, 2, plans, recipes)
        self.assertEqual({'Rice', 'Beans'}, {item['name'] for item in draft.items(start, plans, recipes)})
        draft.set_item_included(start, 'rice:g', False)
        draft.add_plan(start, 1, plans, recipes)
        self.assertEqual({'1', '2'}, draft.selected_plan_ids(start, plans))
        self.assertEqual([], draft.week(start)['excluded'])
        draft.set_item_included(start, 'rice:g', False)
        draft.select_all_plans(start, plans, True, recipes)
        self.assertEqual([], draft.week(start)['excluded'])
        self.assertEqual('200', str(next(item['amount'] for item in draft.items(start, plans, recipes)
                                         if item['name'] == 'Rice')))

    def test_pending_writes_are_durable_before_background_flush(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            scheduled = []
            written = []
            draft.pending_scheduler = scheduled.append
            draft.ingredient_writer = lambda ingredient_id, name, locale: written.append(ingredient_id)
            draft.add_custom('2026-10-05', 'Milk', '1', 'l')
            draft.add_custom('2026-10-05', 'Eggs', '2', 'pcs')
            self.assertEqual([], written)
            self.assertEqual(1, len(scheduled))
            self.assertEqual(2, len(ShoppingDraft(path).pending))
            scheduled[0]()
            self.assertEqual(2, len(written))
            self.assertEqual([], ShoppingDraft(path).pending)

    def test_import_select_remove_and_persist_week(self):
        recipes = [{'id': 'rice-dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'rice-dish', 'servings': 2},
                 {'id': 2, 'recipeId': 'rice-dish', 'servings': 3}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            self.assertEqual(set(), draft.selected_plan_ids('2026-10-05', plans))
            draft.add_all('2026-10-05', plans)
            self.assertEqual({'1', '2'}, draft.selected_plan_ids('2026-10-05', plans))
            self.assertEqual('500', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))
            draft.toggle_plan('2026-10-05', 2)
            self.assertEqual('200', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))
            draft.remove_item('2026-10-05', 'rice:g')
            self.assertEqual([], draft.items('2026-10-05', plans, recipes))
            draft.add_custom('2026-10-05', 'Milk', '2', 'l')
            self.assertEqual('Milk', ShoppingDraft(path).items('2026-10-05', plans, recipes)[0]['name'])
            draft.add_custom('2026-10-05', 'Eggs', '6', 'pcs')
            self.assertEqual(2, len(draft.items('2026-10-05', plans, recipes)))
            self.assertEqual([], draft.items('2026-10-12', plans, recipes))
            draft.add_all('2026-10-05', plans)
            self.assertEqual(3, len(draft.items('2026-10-05', plans, recipes)))
            custom = next(item for item in draft.items('2026-10-05', plans, recipes) if item['name'] == 'Milk')
            draft.remove_item('2026-10-05', item_key(custom))
            self.assertEqual(2, len(draft.items('2026-10-05', plans, recipes)))
            draft.clear('2026-10-05', plans)
            self.assertEqual([], draft.items('2026-10-05', plans, recipes))
            draft.add_all('2026-10-05', plans)
            self.assertEqual('500', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))

    def test_new_plan_requires_explicit_import_and_duplicate_manual_names_remain_separate(self):
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        start = '2026-10-05'
        draft = ShoppingDraft()
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 1}]
        self.assertEqual([], draft.items(start, plans, recipes))
        draft.add_all(start, plans)
        self.assertEqual('100', str(draft.items(start, plans, recipes)[0]['amount']))
        plans.append({'id': 2, 'recipeId': 'dish', 'servings': 2})
        self.assertEqual('100', str(draft.items(start, plans, recipes)[0]['amount']))
        draft.toggle_plan(start, 2)
        self.assertEqual('300', str(draft.items(start, plans, recipes)[0]['amount']))
        draft.toggle_plan(start, 1)
        self.assertEqual('200', str(draft.items(start, plans, recipes)[0]['amount']))
        draft.add_custom(start, 'Eggs', '2', 'pcs')
        draft.add_custom(start, 'Eggs', '4', 'pcs')
        eggs = [item for item in draft.items(start, plans, recipes) if item['name'] == 'Eggs']
        self.assertEqual(2, len(eggs))
        draft.remove_item(start, item_key(eggs[0]))
        self.assertEqual(1, len([item for item in draft.items(start, plans, recipes)
                                 if item['name'] == 'Eggs']))

    def test_selected_catalog_ingredient_uses_stable_id_and_combines_quantity(self):
        draft = ShoppingDraft()
        start = '2026-10-05'
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'karotte', 'name': 'Carrot', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 1}]
        draft.add_all(start, plans)
        draft.add_custom(start, 'Carrot', '50', 'g', ingredient_id='karotte')
        draft.add_custom(start, 'Carrot', '25', 'g', ingredient_id='karotte')
        items = draft.items(start, plans, recipes)
        self.assertEqual(1, len(items))
        self.assertEqual('175', str(items[0]['amount']))

    def test_week_plan_ingredients_can_be_removed_and_restored_after_manual_merge(self):
        start = '2026-10-05'
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 2}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.add_all(start, plans)
            draft.add_custom(start, 'Rice', '50', 'g', ingredient_id='rice')
            self.assertEqual('250', str(draft.items(start, plans, recipes)[0]['amount']))
            draft.remove_item(start, 'rice:g')
            self.assertEqual([], draft.items(start, plans, recipes))
            draft.set_item_included(start, 'rice:g', True)
            self.assertEqual('200', str(ShoppingDraft(path).items(start, plans, recipes)[0]['amount']))
            draft.set_item_included(start, 'rice:g', False)
            draft.add_custom(start, 'Rice', '25', 'g', ingredient_id='rice')
            self.assertEqual('225', str(draft.items(start, plans, recipes)[0]['amount']))

    def test_bulk_meal_and_ingredient_choices_survive_reload(self):
        start = '2026-10-05'
        plans = [{'id': 1}, {'id': 2}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.select_all_plans(start, plans, False)
            self.assertEqual(set(), draft.selected_plan_ids(start, plans))
            draft.select_all_plans(start, plans, True)
            draft.set_item_included(start, 'rice:g', False)
            draft.include_items(start, {'rice:g'})
            restored = ShoppingDraft(path)
            self.assertEqual({'1', '2'}, restored.selected_plan_ids(start, plans))
            self.assertEqual([], restored.week(start)['excluded'])

    def test_legacy_selected_meals_migrate_without_losing_exclusions(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            path.write_text(json.dumps({'version': 1, 'weeks': {start: {
                'plans': ['1'], 'excluded': [], 'custom': [], 'checked': []}}}))
            draft = ShoppingDraft(path)
            plans = [{'id': 1}, {'id': 2}]
            self.assertEqual({'1'}, draft.selected_plan_ids(start, plans))
            self.assertEqual(['1'], ShoppingDraft(path).week(start)['plans'])
            self.assertEqual({'1'}, draft.selected_plan_ids(start, [*plans, {'id': 3}]))

    def test_legacy_implicit_selection_never_imports_week_plans(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            path.write_text(json.dumps({'version': 1, 'weeks': {start: {
                'plans': [], 'excludedPlans': ['2'], 'excluded': [], 'custom': [], 'checked': []}}}))
            draft = ShoppingDraft(path)
            plans = [{'id': 1}, {'id': 2}]
            self.assertEqual(set(), draft.selected_plan_ids(start, plans))
            self.assertEqual(set(), ShoppingDraft(path).selected_plan_ids(start, [*plans, {'id': 3}]))
            self.assertEqual('explicit', ShoppingDraft(path).week(start)['selectionMode'])

    def test_manual_item_validation(self):
        draft = ShoppingDraft()
        for amount in ('0', '-2', 'NaN', 'bad'):
            with self.assertRaises((ValueError, ArithmeticError)):
                draft.add_custom('2026-10-05', 'Eggs', amount, 'pcs')
        with self.assertRaises(ValueError):
            draft.add_custom('2026-10-05', '', '1', 'pcs')
        draft.add_custom('2026-10-05', 'Milk', '1,5', 'l')
        self.assertEqual('1.5', str(draft.items('2026-10-05', [], [])[0]['amount']))

    def test_optional_prices_persist_for_manual_and_planned_items(self):
        start = '2026-10-05'
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 2}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.add_all(start, plans)
            draft.add_custom(start, 'Milk', '2', 'l', '3,50')
            milk = next(item for item in draft.items(start, plans, recipes) if item['name'] == 'Milk')
            self.assertEqual('3.50', str(draft.price_for(start, item_key(milk))))
            draft.set_price(start, 'rice:g', '2.49')
            self.assertEqual('2.49', str(ShoppingDraft(path).price_for(start, 'rice:g')))
            plans[0]['servings'] = 3
            self.assertEqual('300', str(draft.items(start, plans, recipes)[1]['amount']))
            self.assertEqual('2.49', str(draft.price_for(start, 'rice:g')))
            draft.set_price(start, 'rice:g', '')
            self.assertIsNone(ShoppingDraft(path).price_for(start, 'rice:g'))
            draft.remove_item(start, item_key(milk))
            self.assertIsNone(draft.price_for(start, item_key(milk)))
            draft.set_price(start, 'rice:g', '1.00')
            draft.clear(start, plans)
            self.assertIsNone(draft.price_for(start, 'rice:g'))

    def test_price_validation_does_not_change_existing_price(self):
        start = '2026-10-05'
        draft = ShoppingDraft()
        draft.set_price(start, 'rice:g', '1,50')
        for raw in ('-1', '1.001', 'NaN', 'Infinity', 'wrong'):
            with self.assertRaises(ValueError):
                draft.set_price(start, 'rice:g', raw)
            self.assertEqual('1.50', str(draft.price_for(start, 'rice:g')))
        self.assertEqual('0.00', normalize_price('0'))

    def test_reference_price_write_failure_preserves_existing_quote(self):
        draft = ShoppingDraft()
        draft.use_reference_prices({'rice:g': {'price': '1.80', 'basisQuantity': 100}})
        draft.reference_writer = lambda *_: (_ for _ in ()).throw(RuntimeError('offline'))
        with self.assertRaisesRegex(RuntimeError, 'offline'):
            draft.set_reference_price('rice:g', '2.00', 100)
        self.assertEqual('3.60', str(draft.price_for('2026-10-05', 'rice:g', 200)))
        with self.assertRaises(ValueError):
            draft.set_reference_price('rice:g', '2.00', 0)

    def test_reference_price_takes_priority_without_erasing_older_week_price(self):
        draft = ShoppingDraft()
        draft.set_price('2026-10-05', 'rice:g', '9.00')
        draft.set_reference_price('rice:g', '1.80', 100)
        self.assertEqual('3.60', str(draft.price_for('2026-10-05', 'rice:g', 200)))
        self.assertEqual('9.00', str(draft.weekly_price_for('2026-10-05', 'rice:g')))
        draft.set_reference_price('rice:g', '', 100)
        self.assertEqual('9.00', str(draft.price_for('2026-10-05', 'rice:g', 200)))

    def test_database_prices_override_legacy_values_and_failed_writes_preserve_state(self):
        start = '2026-10-05'
        draft = ShoppingDraft()
        draft.set_price(start, 'rice:g', '1.00')
        draft.use_prices(start, {'rice:g': '2.50'})
        self.assertEqual('2.50', str(draft.price_for(start, 'rice:g')))
        calls = []
        draft.price_writer = lambda week, key, price: calls.append((week, key, price))
        draft.set_price(start, 'rice:g', '3,75')
        self.assertEqual((start, 'rice:g', '3.75'), calls[-1])
        self.assertEqual('3.75', str(draft.price_for(start, 'rice:g')))
        draft.price_writer = lambda *_: (_ for _ in ()).throw(RuntimeError('offline'))
        with self.assertRaises(RuntimeError):
            draft.set_price(start, 'rice:g', '4.00')
        self.assertEqual('3.75', str(draft.price_for(start, 'rice:g')))
        with self.assertRaises(ValueError):
            draft.add_custom(start, 'Eggs', '6', 'pcs', '1.234')
        self.assertFalse(draft.week(start)['custom'])

    def test_database_price_writes_do_not_create_a_second_json_price(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.use_prices(start, {})
            writes = []
            draft.price_writer = lambda week, key, price: writes.append((week, key, price))
            draft.set_price(start, 'rice:g', '1.80')
            self.assertEqual([(start, 'rice:g', '1.80')], writes)
            self.assertEqual('1.80', str(draft.weekly_price_for(start, 'rice:g')))
            self.assertEqual({}, draft.week(start)['prices'])
            draft.add_custom(start, 'Milk', '1', 'l', '2.50')
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual({}, saved['weeks'][start]['prices'])

    def test_invalid_draft_is_backed_up_before_new_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            for contents in ('{broken', '[]', '{"version":2,"weeks":{}}',
                             '{"version":1,"weeks":{"2026-10-05":{"plans":[],"excluded":[],"custom":[],"checked":[],"prices":{"rice:g":"bad"}}}}',
                             '{"version":1,"weeks":{"2026-10-05":{"plans":[],"excluded":[],"custom":[{}],"checked":[]}}}'):
                path.write_text(contents, encoding='utf-8')
                draft = ShoppingDraft(path)
                self.assertIn('Original saved to', draft.recovery_notice)
                backup = Path(draft.recovery_notice.split('Original saved to ', 1)[1])
                self.assertEqual(contents, backup.read_text(encoding='utf-8'))
                draft.add_custom('2026-10-05', 'Milk', '1', 'l')
                self.assertEqual('Milk', json.loads(path.read_text())['weeks']['2026-10-05']['custom'][0]['name'])

    def test_interrupted_custom_save_replays_database_writes_once(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.locale = 'de'
            calls = []
            draft.ingredient_writer = lambda *args: calls.append(('ingredient', *args))
            draft.price_writer = lambda *_: (_ for _ in ()).throw(RuntimeError('offline'))
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                draft.add_custom(start, 'Milch', '2', 'l', '3.50')
            saved = ShoppingDraft(path)
            self.assertEqual('Milch', saved.week(start)['custom'][0]['name'])
            self.assertEqual('price', saved.pending[0]['kind'])
            saved.ingredient_writer = lambda *args: calls.append(('ingredient', *args))
            saved.price_writer = lambda *args: calls.append(('price', *args))
            saved.flush_pending()
            self.assertEqual([('ingredient', saved.week(start)['custom'][0]['ingredientId'], 'Milch', 'de'),
                              ('price', start, item_key(saved.week(start)['custom'][0]), '3.50')], calls)
            self.assertEqual([], ShoppingDraft(path).pending)

    def test_interrupted_clear_replays_after_restart(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
            draft.add_custom(start, 'Milk', '1', 'l')
            draft.price_clearer = lambda *_: (_ for _ in ()).throw(RuntimeError('offline'))
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                draft.clear(start)
            saved = ShoppingDraft(path)
            self.assertEqual([], saved.week(start)['custom'])
            calls = []
            saved.price_clearer = lambda week: calls.append(week)
            saved.flush_pending()
            self.assertEqual([start], calls)
            self.assertEqual([], ShoppingDraft(path).pending)


if __name__ == '__main__':
    unittest.main()
