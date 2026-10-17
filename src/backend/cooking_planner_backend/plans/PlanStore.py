"""Persist and localize meal plans."""

from datetime import date
from secrets import randbelow

from cooking_planner_backend.repositories.json_files import read_json, write_json


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError('Date must be an ISO date') from error


class PlanStore:
    def __init__(self, storage, recipes):
        self.storage = storage
        self.recipes = recipes
        self.path = storage.data_dir / 'plans.json'

    def _read(self):
        plans = read_json(self.path, [])
        if not isinstance(plans, list):
            raise ValueError('Unsupported plans file; original was not changed')
        return plans

    def list(self, start, end, locale):
        first, last = _date(start), _date(end)
        if last < first or (last - first).days > 62:
            raise ValueError('Date range must be at most 62 days')
        with self.storage.lock:
            plans = [dict(plan) for plan in self._read() if first <= _date(plan['date']) <= last]
        names = {recipe['id']: recipe['name'] for recipe in self.recipes.list(locale)}
        for plan in plans:
            plan['servings'] = max(1, int(plan.get('servings', 1)))
            plan['recipeTitle'] = names.get(plan['recipeId'], 'Missing recipe')
        return sorted(plans, key=lambda plan: (plan['date'], plan['mealType']))

    def save(self, day, meal_type, recipe_id, servings):
        _date(day)
        if meal_type not in ('BREAKFAST', 'LUNCH', 'DINNER') or type(servings) is not int or not 1 <= servings <= 20:
            raise ValueError('Meal type and 1 to 20 servings are required')
        if recipe_id not in self.recipes.ids():
            raise LookupError('Recipe not found')
        with self.storage.lock:
            plans = self._read()
            existing = next((row for row in plans if row['date'] == day and row['mealType'] == meal_type), None)
            ids = {row['id'] for row in plans}
            new_id = existing['id'] if existing else randbelow(2**63 - 1) + 1
            while new_id in ids and existing is None:
                new_id = randbelow(2**63 - 1) + 1
            plans = [row for row in plans if row['date'] != day or row['mealType'] != meal_type]
            plan = {'id': new_id, 'date': day, 'mealType': meal_type,
                    'recipeId': recipe_id, 'servings': servings, 'recipeTitle': ''}
            plans.append(plan)
            write_json(self.path, plans)
        return {**plan, 'recipeTitle': self.recipes.get('en', recipe_id)['name']
                if recipe_id in self.recipes._catalog('en')[1] else 'Missing recipe'}

    def delete(self, plan_id):
        with self.storage.lock:
            plans = self._read()
            remaining = [row for row in plans if row.get('id') != plan_id]
            if len(remaining) == len(plans):
                raise LookupError('Plan not found')
            write_json(self.path, remaining)
