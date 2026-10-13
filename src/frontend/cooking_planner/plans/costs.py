"""Estimate ingredient costs for the recipes planned on each day."""

from collections import defaultdict
from decimal import Decimal

from cooking_planner.shopping.ShoppingDraft import item_key


def planned_costs(start, plans, recipes, draft):
    """Return dated partial totals and coverage for all planned recipes.

    Reference prices cover their saved basis quantity. Older week prices cover
    the week's planned quantity and are split among its meals. Shopping list
    selections do not change the cost of recipes that remain on the plan.
    """
    by_recipe = {recipe['id']: recipe for recipe in recipes}
    planned = [(plan, by_recipe[plan['recipeId']]) for plan in plans
               if plan['recipeId'] in by_recipe]
    quantities = defaultdict(lambda: Decimal('0'))
    for plan, recipe in planned:
        for ingredient in recipe['ingredients']:
            quantities[item_key(ingredient)] += (Decimal(str(ingredient['amount']))
                                                 * Decimal(str(plan['servings'])))
    totals = defaultdict(lambda: Decimal('0'))
    coverage = defaultdict(lambda: [0, 0])
    for plan, recipe in planned:
        day = plan['date']
        for ingredient in recipe['ingredients']:
            key = item_key(ingredient)
            coverage[day][1] += 1
            quantity = Decimal(str(ingredient['amount'])) * Decimal(str(plan['servings']))
            reference = draft.reference_price_for(key)
            if reference is not None:
                price, basis = reference
                totals[day] += price * quantity / basis
                coverage[day][0] += 1
                continue
            price = draft.weekly_price_for(start, key)
            if price is None:
                continue
            if quantities[key] <= 0:
                continue
            totals[day] += price * quantity / quantities[key]
            coverage[day][0] += 1
    return {day: (totals[day], *counts) for day, counts in coverage.items()}
