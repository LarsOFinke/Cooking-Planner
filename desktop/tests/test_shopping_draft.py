import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cooking_planner.shopping.draft import ShoppingDraft, item_key


class ShoppingDraftTest(unittest.TestCase):
    def test_import_select_remove_and_persist_week(self):
        recipes = [{'id': 'rice-dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        plans = [{'id': 1, 'recipeId': 'rice-dish', 'servings': 2},
                 {'id': 2, 'recipeId': 'rice-dish', 'servings': 3}]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            draft = ShoppingDraft(path)
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
            self.assertEqual('500', str(draft.items('2026-10-12', plans, recipes)[0]['amount']))
            draft.add_all('2026-10-05', plans)
            self.assertEqual(3, len(draft.items('2026-10-05', plans, recipes)))
            custom = next(item for item in draft.items('2026-10-05', plans, recipes) if item['name'] == 'Milk')
            draft.remove_item('2026-10-05', item_key(custom))
            self.assertEqual(2, len(draft.items('2026-10-05', plans, recipes)))
            draft.clear('2026-10-05', plans)
            self.assertEqual([], draft.items('2026-10-05', plans, recipes))
            draft.add_all('2026-10-05', plans)
            self.assertEqual('500', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))

    def test_new_plan_is_included_and_duplicate_manual_names_remain_separate(self):
        recipes = [{'id': 'dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'amount': 100, 'unit': 'g'}]}]
        start = '2026-10-05'
        draft = ShoppingDraft()
        plans = [{'id': 1, 'recipeId': 'dish', 'servings': 1}]
        self.assertEqual('100', str(draft.items(start, plans, recipes)[0]['amount']))
        plans.append({'id': 2, 'recipeId': 'dish', 'servings': 2})
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

    def test_legacy_selected_meals_migrate_without_losing_exclusions(self):
        start = '2026-10-05'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            path.write_text(json.dumps({'version': 1, 'weeks': {start: {
                'plans': ['1'], 'excluded': [], 'custom': [], 'checked': []}}}))
            draft = ShoppingDraft(path)
            plans = [{'id': 1}, {'id': 2}]
            self.assertEqual({'1'}, draft.selected_plan_ids(start, plans))
            self.assertEqual(['2'], ShoppingDraft(path).week(start)['excludedPlans'])
            self.assertEqual({'1', '3'}, draft.selected_plan_ids(start, [*plans, {'id': 3}]))

    def test_manual_item_validation(self):
        draft = ShoppingDraft()
        for amount in ('0', '-2', 'NaN', 'bad'):
            with self.assertRaises((ValueError, ArithmeticError)):
                draft.add_custom('2026-10-05', 'Eggs', amount, 'pcs')
        with self.assertRaises(ValueError):
            draft.add_custom('2026-10-05', '', '1', 'pcs')
        draft.add_custom('2026-10-05', 'Milk', '1,5', 'l')
        self.assertEqual('1.5', str(draft.items('2026-10-05', [], [])[0]['amount']))

    def test_invalid_draft_is_backed_up_before_new_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'shopping.json'
            for contents in ('{broken', '[]', '{"version":2,"weeks":{}}',
                             '{"version":1,"weeks":{"2026-10-05":{"plans":[],"excluded":[],"custom":[{}],"checked":[]}}}'):
                path.write_text(contents, encoding='utf-8')
                draft = ShoppingDraft(path)
                self.assertIn('Original saved to', draft.recovery_notice)
                backup = Path(draft.recovery_notice.split('Original saved to ', 1)[1])
                self.assertEqual(contents, backup.read_text(encoding='utf-8'))
                draft.add_custom('2026-10-05', 'Milk', '1', 'l')
                self.assertEqual('Milk', json.loads(path.read_text())['weeks']['2026-10-05']['custom'][0]['name'])


if __name__ == '__main__':
    unittest.main()
