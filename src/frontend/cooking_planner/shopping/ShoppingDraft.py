"""Persist shopping choices and project upcoming planned meals into a list."""

import json
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from threading import RLock
from uuid import uuid4

from cooking_planner.pricing import normalize_price
from cooking_planner.shopping.persistence import load_draft, save_draft

UPCOMING = 'upcoming'


def item_key(item: dict) -> str:
    return f"{item['ingredientId']}:{item['unit']}"


class ShoppingDraft:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.weeks = {}
        self.pending = []
        self._pending_lock = RLock()
        self._flush_scheduled = False
        self.pending_scheduler = None
        self.database_prices = {}
        self.reference_prices = {}
        self.price_writer = None
        self.reference_writer = None
        self.price_clearer = None
        self.ingredient_writer = None
        self.locale = 'en'
        self.recovery_notice = None
        if path:
            self.weeks, self.pending, self.recovery_notice = load_draft(path)

    def week(self, start: str) -> dict:
        return self.weeks.setdefault(start, {'plans': [], 'selectionMode': 'auto' if start == UPCOMING else 'explicit',
                                             'excludedPlans': [], 'excluded': [], 'custom': [],
                                             'checked': [], 'boughtPlans': {}, 'prices': {}})

    def use_upcoming(self, current_week: str) -> bool:
        """Carry the current shopping list into the persistent upcoming list once."""
        if UPCOMING in self.weeks:
            return False
        previous = self.weeks.get(current_week)
        state = deepcopy(previous) if previous else self.week(UPCOMING)
        state['plans'] = []
        state['selectionMode'] = 'auto'
        state['excludedPlans'] = []
        state['boughtPlans'] = {}
        self.weeks[UPCOMING] = state
        self.save()
        return True

    def use_prices(self, start: str, prices: dict[str, str]) -> None:
        """Use database prices for a loaded week; legacy JSON remains a migration source."""
        self.database_prices[start] = dict(prices)

    def use_reference_prices(self, prices: dict[str, dict]) -> None:
        self.reference_prices = dict(prices)

    def reference_price_for(self, key: str) -> tuple[Decimal, Decimal] | None:
        quote = self.reference_prices.get(key)
        if quote is None:
            return None
        return Decimal(quote['price']), Decimal(str(quote['basisQuantity']))

    def selected_plan_ids(self, start: str, plans: list[dict]) -> set[str]:
        state = self.week(start)
        available = {str(plan['id']) for plan in plans}
        if start == UPCOMING:
            return available - set(state.get('excludedPlans', []))
        if state.get('selectionMode') != 'explicit':
            # Older drafts could implicitly include every plan except excludedPlans.
            # Only persisted positive selections can be migrated without making
            # newly planned meals appear in Shopping on the first read.
            state['plans'] = sorted(set(state['plans']) & available)
            state.pop('excludedPlans', None)
            state['selectionMode'] = 'explicit'
            self.save()
        return set(state['plans']) & available

    def save(self) -> None:
        if self.path is None:
            return
        with self._pending_lock:
            save_draft(self.path, self.weeks, self.pending)

    def schedule_pending(self) -> None:
        with self._pending_lock:
            if not self.pending or self._flush_scheduled:
                return
            self._flush_scheduled = True
        if self.pending_scheduler is None:
            self.flush_pending()
        else:
            self.pending_scheduler(self.flush_pending)

    def flush_pending(self) -> None:
        """Replay durable, idempotent backend writes after an interrupted save."""
        drained = False
        try:
            while True:
                with self._pending_lock:
                    if not self.pending:
                        drained = True
                        return
                    operation = self.pending[0]
                if operation['kind'] == 'ingredient':
                    if self.ingredient_writer is None:
                        return
                    self.ingredient_writer(operation['id'], operation['name'], operation['locale'])
                elif operation['kind'] == 'price':
                    if self.price_writer is None:
                        return
                    self.price_writer(operation['week'], operation['key'], operation['price'])
                else:
                    if self.price_clearer is None:
                        return
                    self.price_clearer(operation['week'])
                with self._pending_lock:
                    self.pending.pop(0)
                    self.save()
        finally:
            with self._pending_lock:
                self._flush_scheduled = False
                added_during_flush = drained and bool(self.pending)
            if added_during_flush:
                self.schedule_pending()

    def _queue(self, *operations: dict) -> None:
        with self._pending_lock:
            self.pending.extend(operations)
            self.save()
        self.schedule_pending()

    def add_all(self, start: str, plans: list[dict]) -> None:
        state = self.week(start)
        if start == UPCOMING:
            state['excludedPlans'] = []
            state['excluded'] = []
            state['checked'] = []
            self.save()
            return
        state['plans'] = [str(plan['id']) for plan in plans]
        state['selectionMode'] = 'explicit'
        state.pop('excludedPlans', None)
        state['excluded'] = []
        state['checked'] = []
        self.save()

    @staticmethod
    def _restore_plan_ingredients(state: dict, plans: list[dict], recipes: list[dict],
                                  plan_ids: set[str]) -> None:
        if not recipes or not state['excluded']:
            return
        by_id = {recipe['id']: recipe for recipe in recipes}
        included = {item_key(item)
                    for plan in plans if str(plan['id']) in plan_ids
                    for item in by_id.get(plan.get('recipeId'), {}).get('ingredients', [])}
        state['excluded'] = [key for key in state['excluded'] if key not in included]

    def add_day(self, start: str, plans: list[dict], day: str,
                recipes: list[dict] | None = None) -> int:
        """Include every planned meal on one selected date."""
        if not any(plan['date'] == day for plan in plans):
            return 0
        self.selected_plan_ids(start, plans)
        chosen = [str(plan['id']) for plan in plans if plan['date'] == day]
        state = self.week(start)
        if start == UPCOMING:
            state['excludedPlans'] = [key for key in state['excludedPlans'] if key not in chosen]
            self._restore_plan_ingredients(state, plans, recipes or [], set(chosen))
            self.save()
            return len(chosen)
        state['plans'] = sorted(set(state['plans']) | set(chosen))
        self._restore_plan_ingredients(state, plans, recipes or [], set(chosen))
        self.save()
        return len(chosen)

    def toggle_plan(self, start: str, plan_id: int, plans: list[dict] | None = None,
                    recipes: list[dict] | None = None) -> None:
        state = self.week(start)
        if start == UPCOMING:
            excluded = state['excludedPlans']
            key = str(plan_id)
            if key in excluded:
                excluded.remove(key)
                self._restore_plan_ingredients(state, plans or [], recipes or [], {key})
            else:
                excluded.append(key)
            self.save()
            return
        selected = state['plans']
        key = str(plan_id)
        if key in selected:
            selected.remove(key)
        else:
            selected.append(key)
            self._restore_plan_ingredients(state, plans or [], recipes or [], {key})
        self.save()

    def add_plan(self, start: str, plan_id: int, plans: list[dict], recipes: list[dict]) -> None:
        """Import one meal, or restore its ingredients if it was already selected."""
        self.selected_plan_ids(start, plans)
        key = str(plan_id)
        if not any(str(plan['id']) == key for plan in plans):
            return
        state = self.week(start)
        if start == UPCOMING:
            if key in state['excludedPlans']:
                state['excludedPlans'].remove(key)
            self._restore_plan_ingredients(state, plans, recipes, {key})
            self.save()
            return
        if key not in state['plans']:
            state['plans'].append(key)
        self._restore_plan_ingredients(state, plans, recipes, {key})
        self.save()

    def select_all_plans(self, start: str, plans: list[dict], selected: bool,
                         recipes: list[dict] | None = None) -> None:
        state = self.week(start)
        if start == UPCOMING:
            state['excludedPlans'] = [] if selected else [str(plan['id']) for plan in plans]
            if selected:
                self._restore_plan_ingredients(state, plans, recipes or [],
                                               {str(plan['id']) for plan in plans})
            self.save()
            return
        state['plans'] = [str(plan['id']) for plan in plans] if selected else []
        if selected:
            self._restore_plan_ingredients(state, plans, recipes or [], set(state['plans']))
        state['selectionMode'] = 'explicit'
        state.pop('excludedPlans', None)
        self.save()

    def set_item_included(self, start: str, key: str, included: bool) -> None:
        state = self.week(start)
        excluded = state['excluded']
        if included and key in excluded:
            excluded.remove(key)
        elif not included and key not in excluded:
            excluded.append(key)
            if key in state['checked']:
                state['checked'].remove(key)
        self.save()

    def include_items(self, start: str, keys: set[str]) -> None:
        state = self.week(start)
        state['excluded'] = [key for key in state['excluded'] if key not in keys]
        self.save()

    def add_custom(self, start: str, name: str, amount: str, unit: str, price: str = '',
                   ingredient_id: str | None = None) -> None:
        quantity = Decimal(amount.strip().replace(',', '.'))
        if (not name.strip() or not unit.strip() or len(name.strip()) > 120 or len(unit.strip()) > 24
                or not quantity.is_finite() or quantity <= 0 or quantity > 1_000_000):
            raise ValueError('Name, positive quantity, and unit are required')
        normalized = normalize_price(price)
        item = {'ingredientId': ingredient_id or 'custom-' + uuid4().hex,
                'name': name.strip(), 'amount': str(quantity), 'unit': unit.strip(), 'recipeCount': 0}
        state = self.week(start)
        state['custom'].append(item)
        if normalized is not None:
            if self.price_writer is None or start == UPCOMING:
                state.setdefault('prices', {})[item_key(item)] = normalized
            else:
                self.database_prices.setdefault(start, {})[item_key(item)] = normalized
        if item_key(item) in state['excluded']:
            state['excluded'].remove(item_key(item))
        operations = []
        if ingredient_id is None and self.ingredient_writer is not None:
            operations.append({'kind': 'ingredient', 'id': item['ingredientId'],
                               'name': item['name'], 'locale': self.locale})
        if normalized is not None and self.price_writer is not None and start != UPCOMING:
            operations.append({'kind': 'price', 'week': start, 'key': item_key(item), 'price': normalized})
        self._queue(*operations)

    def weekly_price_for(self, start: str, key: str) -> Decimal | None:
        source = self.database_prices.get(start)
        value = (source if source is not None else self.week(start).get('prices', {})).get(key)
        return Decimal(value) if value is not None else None

    def price_for(self, start: str, key: str, amount=None) -> Decimal | None:
        quote = self.reference_price_for(key)
        if quote is not None and amount is not None:
            price, basis = quote
            return price * Decimal(str(amount)) / basis
        return self.weekly_price_for(start, key)

    def set_reference_price(self, key: str, price: str, basis_quantity: int) -> None:
        normalized = normalize_price(price)
        if not isinstance(basis_quantity, int) or not 0 < basis_quantity <= 1_000_000:
            raise ValueError('Enter a positive price quantity')
        if self.reference_writer is not None:
            self.reference_writer(key, normalized or '', basis_quantity)
        if normalized is None:
            self.reference_prices.pop(key, None)
        else:
            self.reference_prices[key] = {'price': normalized, 'basisQuantity': basis_quantity}

    def set_price(self, start: str, key: str, price: str) -> None:
        normalized = normalize_price(price)
        if self.price_writer is None or start == UPCOMING:
            prices = self.week(start).setdefault('prices', {})
            if normalized is None:
                prices.pop(key, None)
            else:
                prices[key] = normalized
            self.save()
        else:
            self._queue({'kind': 'price', 'week': start, 'key': key, 'price': normalized or ''})
            prices = self.database_prices.setdefault(start, {})
            if normalized is None:
                prices.pop(key, None)
            else:
                prices[key] = normalized

    def remove_item(self, start: str, key: str) -> None:
        state = self.week(start)
        clear_price = start != UPCOMING and self.price_writer is not None and self.weekly_price_for(start, key) is not None
        state.setdefault('prices', {}).pop(key, None)
        if start in self.database_prices:
            self.database_prices[start].pop(key, None)
        state['custom'] = [item for item in state['custom'] if item_key(item) != key]
        if key not in state['excluded']:
            state['excluded'].append(key)
        if key in state['checked']:
            state['checked'].remove(key)
        self._queue(*([{'kind': 'price', 'week': start, 'key': key, 'price': ''}] if clear_price else []))

    def toggle_checked(self, start: str, key: str) -> None:
        checked = self.week(start)['checked']
        if key in checked:
            checked.remove(key)
        else:
            checked.append(key)
        self.save()

    @staticmethod
    def _plan_signature(plan: dict, recipe: dict) -> str:
        ingredients = sorted((item_key(item), str(item['amount'])) for item in recipe['ingredients'])
        contents = json.dumps([plan['recipeId'], plan['servings'], ingredients], separators=(',', ':'))
        return sha256(contents.encode('utf-8')).hexdigest()

    def bought_plan_ids(self, start: str, plans: list[dict], recipes: list[dict]) -> set[str]:
        state = self.week(start)
        checked = set(state['checked']) - set(state['excluded'])
        by_recipe = {recipe['id']: recipe for recipe in recipes}
        selected = self.selected_plan_ids(start, plans)
        bought = state.get('boughtPlans', {})
        return {str(plan['id']) for plan in plans if str(plan['id']) in selected
                and (recipe := by_recipe.get(plan['recipeId'])) is not None
                and recipe['ingredients']
                and all(item_key(item) in checked for item in recipe['ingredients'])
                and bought.get(str(plan['id'])) == self._plan_signature(plan, recipe)}

    def update_bought_plans(self, start: str, plans: list[dict], recipes: list[dict]) -> None:
        state = self.week(start)
        checked = set(state['checked']) - set(state['excluded'])
        by_recipe = {recipe['id']: recipe for recipe in recipes}
        selected = self.selected_plan_ids(start, plans)
        bought = state.setdefault('boughtPlans', {})
        for key in set(bought) - {str(plan['id']) for plan in plans}:
            bought.pop(key, None)
        for plan in plans:
            key = str(plan['id'])
            recipe = by_recipe.get(plan['recipeId'])
            if key in selected and recipe and recipe['ingredients'] and all(
                    item_key(item) in checked for item in recipe['ingredients']):
                bought[key] = self._plan_signature(plan, recipe)
            else:
                bought.pop(key, None)
        self.save()

    def reset_checks(self, start: str) -> None:
        self.week(start)['checked'] = []
        self.save()

    def clear(self, start: str, plans: list[dict] | None = None) -> None:
        old_prices = list(self.database_prices.get(start, self.week(start).get('prices', {})))
        self.database_prices.pop(start, None)
        self.weeks[start] = {'plans': [], 'selectionMode': 'auto' if start == UPCOMING else 'explicit',
                             'excludedPlans': [str(plan['id']) for plan in plans or []] if start == UPCOMING else [],
                             'excluded': [], 'custom': [], 'checked': [], 'boughtPlans': {}, 'prices': {}}
        if start == UPCOMING:
            self.save()
        elif self.price_clearer is not None:
            self._queue({'kind': 'clear_prices', 'week': start})
        elif self.price_writer is not None:
            self._queue(*({'kind': 'price', 'week': start, 'key': key, 'price': ''} for key in old_prices))
        else:
            self.save()

    def planned_items(self, start: str, plans: list[dict], recipes: list[dict]) -> list[dict]:
        """Project the selected backend plans through the current recipe catalog."""
        selected = self.selected_plan_ids(start, plans)
        by_id = {recipe['id']: recipe for recipe in recipes}
        combined = {}
        for plan in plans:
            if str(plan['id']) not in selected:
                continue
            recipe = by_id.get(plan['recipeId'])
            if recipe is None:
                continue
            for ingredient in recipe['ingredients']:
                key = item_key(ingredient)
                amount = Decimal(str(ingredient['amount'])) * Decimal(str(plan['servings']))
                if key in combined:
                    combined[key]['amount'] += amount
                    combined[key]['recipeCount'] += 1
                else:
                    combined[key] = {'ingredientId': ingredient['ingredientId'], 'name': ingredient['name'],
                                     'amount': amount, 'unit': ingredient['unit'], 'recipeCount': 1}
        return sorted(combined.values(), key=lambda item: item['name'].casefold())

    def items(self, start: str, plans: list[dict], recipes: list[dict]) -> list[dict]:
        state = self.week(start)
        combined = {item_key(item): item for item in self.planned_items(start, plans, recipes)}
        for item in state['custom']:
            key = item_key(item)
            if key in combined:
                combined[key]['amount'] += Decimal(str(item['amount']))
            else:
                combined[key] = {**item, 'amount': Decimal(str(item['amount']))}
        return sorted((item for key, item in combined.items() if key not in state['excluded']),
                      key=lambda item: item['name'].casefold())
