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
            self.assertEqual([], draft.items('2026-10-05', plans, recipes))
            draft.add_all('2026-10-05', plans)
            self.assertEqual('500', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))
            draft.toggle_plan('2026-10-05', 2)
            self.assertEqual('200', str(draft.items('2026-10-05', plans, recipes)[0]['amount']))
            draft.remove_item('2026-10-05', 'rice:g')
            self.assertEqual([], draft.items('2026-10-05', plans, recipes))
            draft.add_custom('2026-10-05', 'Milk', '2', 'l')
            self.assertEqual('Milk', ShoppingDraft(path).items('2026-10-05', plans, recipes)[0]['name'])
            self.assertEqual([], draft.items('2026-10-12', plans, recipes))
            draft.add_all('2026-10-05', plans)
            self.assertEqual(2, len(draft.items('2026-10-05', plans, recipes)))
            custom = next(item for item in draft.items('2026-10-05', plans, recipes) if item['name'] == 'Milk')
            draft.remove_item('2026-10-05', item_key(custom))
            self.assertEqual(1, len(draft.items('2026-10-05', plans, recipes)))

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
