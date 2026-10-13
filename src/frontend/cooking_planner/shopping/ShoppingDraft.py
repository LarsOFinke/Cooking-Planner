"""A user-controlled, week-specific shopping draft built from planned meals."""

from decimal import Decimal
from pathlib import Path
from threading import RLock
from uuid import uuid4

from cooking_planner.pricing import normalize_price
from cooking_planner.shopping.persistence import load_draft, save_draft


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
        return self.weeks.setdefault(start, {'plans': [], 'excludedPlans': [], 'excluded': [],
                                             'custom': [], 'checked': [], 'prices': {}})

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
        if 'excludedPlans' not in state:
            # Old drafts stored an explicit selection. Preserve a nonempty
            # selection once, then include future plans automatically.
            selected = set(state['plans'])
            state['excludedPlans'] = ([str(plan['id']) for plan in plans
                                       if str(plan['id']) not in selected] if selected else [])
            self.save()
        excluded = set(state['excludedPlans'])
        return {str(plan['id']) for plan in plans if str(plan['id']) not in excluded}

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
        state['excludedPlans'] = []
        state['excluded'] = []
        state['checked'] = []
        self.save()

    def add_day(self, start: str, plans: list[dict], day: str) -> int:
        """Include every planned meal on one selected date."""
        if not any(plan['date'] == day for plan in plans):
            return 0
        self.selected_plan_ids(start, plans)
        excluded = self.week(start)['excludedPlans']
        chosen = {str(plan['id']) for plan in plans if plan['date'] == day}
        self.week(start)['excludedPlans'] = [plan_id for plan_id in excluded if plan_id not in chosen]
        self.save()
        return len(chosen)

    def toggle_plan(self, start: str, plan_id: int) -> None:
        excluded = self.week(start).setdefault('excludedPlans', [])
        key = str(plan_id)
        if key in excluded:
            excluded.remove(key)
        else:
            excluded.append(key)
        self.save()

    def select_all_plans(self, start: str, plans: list[dict], selected: bool) -> None:
        self.week(start)['excludedPlans'] = [] if selected else [str(plan['id']) for plan in plans]
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
            if self.price_writer is None:
                state.setdefault('prices', {})[item_key(item)] = normalized
            else:
                self.database_prices.setdefault(start, {})[item_key(item)] = normalized
        if item_key(item) in state['excluded']:
            state['excluded'].remove(item_key(item))
        operations = []
        if ingredient_id is None and self.ingredient_writer is not None:
            operations.append({'kind': 'ingredient', 'id': item['ingredientId'],
                               'name': item['name'], 'locale': self.locale})
        if normalized is not None and self.price_writer is not None:
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
        if self.price_writer is None:
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
        clear_price = self.price_writer is not None and self.weekly_price_for(start, key) is not None
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

    def reset_checks(self, start: str) -> None:
        self.week(start)['checked'] = []
        self.save()

    def clear(self, start: str, plans: list[dict] | None = None) -> None:
        old_prices = list(self.database_prices.get(start, self.week(start).get('prices', {})))
        self.database_prices.pop(start, None)
        self.weeks[start] = {'plans': [], 'excludedPlans': [str(plan['id']) for plan in (plans or [])],
                             'excluded': [], 'custom': [], 'checked': [], 'prices': {}}
        if self.price_clearer is not None:
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
