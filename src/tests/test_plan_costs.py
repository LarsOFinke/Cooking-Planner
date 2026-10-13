import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.plans.costs import planned_costs
from cooking_planner.shopping.ShoppingDraft import ShoppingDraft


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
        self.assertEqual({start: (Decimal('5.00'), 2, 2),
                          '2026-10-06': (Decimal('3.00'), 1, 1)},
                         planned_costs(start, plans, recipes, draft))

    def test_reference_price_scales_with_recipe_quantity_and_is_reused(self):
        start = '2026-10-05'
        recipes = [{'id': 'rice-dish', 'ingredients': [
            {'ingredientId': 'rice', 'name': 'Rice', 'unit': 'g', 'amount': 150},
            {'ingredientId': 'oil', 'name': 'Oil', 'unit': 'ml', 'amount': 50},
            {'ingredientId': 'egg', 'name': 'Egg', 'unit': 'pcs', 'amount': 1}]}]
        plans = [{'id': 1, 'date': start, 'recipeId': 'rice-dish', 'servings': 2}]
        draft = ShoppingDraft()
        draft.set_reference_price('rice:g', '1.80', 100)
        draft.set_reference_price('oil:ml', '2.20', 100)
        draft.set_reference_price('egg:pcs', '0.50', 1)
        self.assertEqual(Decimal('5.40'), draft.price_for(start, 'rice:g', 300))
        self.assertEqual((Decimal('8.60'), 3, 3), planned_costs(start, plans, recipes, draft)[start])
        next_week = '2026-10-12'
        plans[0]['date'] = next_week
        self.assertEqual((Decimal('8.60'), 3, 3), planned_costs(next_week, plans, recipes, draft)[next_week])

    def test_day_total_adds_planned_recipes_and_reports_unpriced_ingredients(self):
        start = '2026-10-05'
        recipes = [
            {'id': 'one', 'ingredients': [
                {'ingredientId': 'rice', 'unit': 'g', 'amount': 100},
                {'ingredientId': 'oil', 'unit': 'ml', 'amount': 10}]},
            {'id': 'two', 'ingredients': [
                {'ingredientId': 'rice', 'unit': 'g', 'amount': 200},
                {'ingredientId': 'spice', 'unit': 'g', 'amount': 5}]},
        ]
        plans = [{'id': 1, 'date': start, 'recipeId': 'one', 'servings': 2},
                 {'id': 2, 'date': start, 'recipeId': 'two', 'servings': 1}]
        draft = ShoppingDraft()
        draft.set_reference_price('rice:g', '1.80', 100)
        draft.set_reference_price('oil:ml', '2.20', 100)
        expected = {start: (Decimal('7.64'), 3, 4)}
        self.assertEqual(expected, planned_costs(start, plans, recipes, draft))
        draft.toggle_plan(start, 2)
        draft.remove_item(start, 'rice:g')
        self.assertEqual(expected, planned_costs(start, plans, recipes, draft))


if __name__ == '__main__':
    unittest.main()
