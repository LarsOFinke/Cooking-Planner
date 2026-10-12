"""Allocate priced shopping ingredients to the planned meals that use them."""

from collections import defaultdict
from decimal import Decimal

from cooking_planner.shopping.draft import item_key


def planned_costs(start, plans, recipes, draft):
    """Return dated partial totals and coverage for selected planned meals.

    Reference prices cover their saved basis quantity. Older week prices cover
    the displayed shopping quantity and are split among the planned meals.
    Unpriced, removed, and excluded ingredients do not contribute a cost.
    """
    selected = draft.selected_plan_ids(start, plans)
    listed = {item_key(item): item for item in draft.items(start, plans, recipes)}
    by_recipe = {recipe['id']: recipe for recipe in recipes}
    totals = defaultdict(lambda: Decimal('0'))
    coverage = defaultdict(lambda: [0, 0])
    for plan in plans:
        if str(plan['id']) not in selected:
            continue
        recipe = by_recipe.get(plan['recipeId'])
        if recipe is None:
            continue
        day = plan['date']
        for ingredient in recipe['ingredients']:
            key = item_key(ingredient)
            coverage[day][1] += 1
            item = listed.get(key)
            if item is None:
                continue
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
            listed_quantity = Decimal(str(item['amount']))
            if listed_quantity <= 0:
                continue
            totals[day] += price * quantity / listed_quantity
            coverage[day][0] += 1
    return {day: (totals[day], *counts) for day, counts in coverage.items()}
