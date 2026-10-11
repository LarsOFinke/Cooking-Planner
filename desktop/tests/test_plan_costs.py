import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cooking_planner.plans.costs import planned_costs
from cooking_planner.shopping.draft import ShoppingDraft


class PlannedCostsTest(unittest.TestCase):
    def test_shared_ingredient_price_is_split_by_quantity_and_servings(self):
        start = '2026-10-05'
        recipes = [
            {'id': 'small', 'ingredients': [
                {'ingredientId': 'rice', 'name': 'Rice', 'unit': 'g', 'amount': 100},
                {'ingredientId': 'oil', 'name': 'Oil', 'unit': 'ml', 'amount': 10}]},
            {'id': 'large', 'ingredients': [
                {'ingredientId': 'rice', 'name': 'Rice', 'unit': 'g', 'amount': 200}]},
        ]
        plans = [
            {'id': 1, 'date': start, 'recipeId': 'small', 'servings': 2},
            {'id': 2, 'date': '2026-10-06', 'recipeId': 'large', 'servings': 1},
        ]
        draft = ShoppingDraft()
        draft.set_price(start, 'rice:g', '6.00')
        self.assertEqual({start: (Decimal('3.00'), 1, 2),
                          '2026-10-06': (Decimal('3.00'), 1, 1)},
                         planned_costs(start, plans, recipes, draft))
        draft.set_price(start, 'oil:ml', '2.00')
        self.assertEqual((Decimal('5.00'), 2, 2), planned_costs(start, plans, recipes, draft)[start])
        draft.toggle_plan(start, 2)
        self.assertEqual({start: (Decimal('8.00'), 2, 2)}, planned_costs(start, plans, recipes, draft))


if __name__ == '__main__':
    unittest.main()
