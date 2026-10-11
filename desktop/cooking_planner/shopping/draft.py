"""A user-controlled, week-specific shopping draft built from planned meals."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4


def item_key(item: dict) -> str:
    return f"{item['ingredientId']}:{item['unit']}"


def normalize_price(raw: str) -> str | None:
    """Normalize an optional euro price for the complete listed quantity."""
    value = raw.strip().replace(',', '.')
    if not value:
        return None
    try:
        price = Decimal(value)
        cents = price.quantize(Decimal('0.01'))
    except InvalidOperation as error:
        raise ValueError('Enter a price with at most two decimal places') from error
    if not price.is_finite() or price < 0 or price > 1_000_000 or price != cents:
        raise ValueError('Enter a non-negative price with at most two decimal places')
    return format(cents, '.2f')


def valid_week(state: object) -> bool:
    if not isinstance(state, dict):
        return False
    if any(not isinstance(state.get(key), list) for key in ('plans', 'excluded', 'custom', 'checked')):
        return False
    if any(not isinstance(value, str) for key in ('plans', 'excluded', 'checked') for value in state[key]):
        return False
    if 'excludedPlans' in state and (not isinstance(state['excludedPlans'], list) or
                                     any(not isinstance(value, str) for value in state['excludedPlans'])):
        return False
    prices = state.get('prices', {})
    if not isinstance(prices, dict):
        return False
    for key, value in prices.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return False
        try:
            if normalize_price(value) is None:
                return False
        except ValueError:
            return False
    for item in state['custom']:
        if (not isinstance(item, dict) or
                any(not isinstance(item.get(key), str) for key in ('ingredientId', 'name', 'unit'))):
            return False
        try:
            if not Decimal(str(item['amount'])).is_finite():
                return False
        except (KeyError, ValueError, InvalidOperation):
            return False
    return True


class ShoppingDraft:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.weeks = {}
        self.recovery_notice = None
        if path and path.is_file():
            try:
                document = json.loads(path.read_text(encoding='utf-8'))
                if (not isinstance(document, dict) or document.get('version') != 1
                        or not isinstance(document.get('weeks'), dict)
                        or any(not isinstance(week, str) or not valid_week(state)
                               for week, state in document['weeks'].items())):
                    raise ValueError('Unsupported shopping draft format')
                self.weeks = document['weeks']
            except (ValueError, TypeError, AttributeError):
                backup = path.with_name(f'{path.name}.invalid-{uuid4().hex}.bak')
                with path.open('rb') as source, backup.open('xb') as destination:
                    copyfileobj(source, destination)
                self.recovery_notice = f'Shopping draft could not be read. Original saved to {backup}'

    def week(self, start: str) -> dict:
        return self.weeks.setdefault(start, {'plans': [], 'excludedPlans': [], 'excluded': [],
                                             'custom': [], 'checked': [], 'prices': {}})

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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version': 1, 'weeks': self.weeks}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.path)

    def add_all(self, start: str, plans: list[dict]) -> None:
        state = self.week(start)
        state['excludedPlans'] = []
        state['excluded'] = []
        state['checked'] = []
        self.save()

    def toggle_plan(self, start: str, plan_id: int) -> None:
        excluded = self.week(start).setdefault('excludedPlans', [])
        key = str(plan_id)
        if key in excluded:
            excluded.remove(key)
        else:
            excluded.append(key)
        self.save()

    def add_custom(self, start: str, name: str, amount: str, unit: str, price: str = '') -> None:
        quantity = Decimal(amount.strip().replace(',', '.'))
        if (not name.strip() or not unit.strip() or len(name.strip()) > 120 or len(unit.strip()) > 24
                or not quantity.is_finite() or quantity <= 0 or quantity > 1_000_000):
            raise ValueError('Name, positive quantity, and unit are required')
        normalized = normalize_price(price)
        item = {'ingredientId': 'custom-' + uuid4().hex,
                'name': name.strip(), 'amount': str(quantity), 'unit': unit.strip(), 'recipeCount': 0}
        state = self.week(start)
        state['custom'].append(item)
        if normalized is not None:
            state.setdefault('prices', {})[item_key(item)] = normalized
        self.save()

    def price_for(self, start: str, key: str) -> Decimal | None:
        value = self.week(start).get('prices', {}).get(key)
        return Decimal(value) if value is not None else None

    def set_price(self, start: str, key: str, price: str) -> None:
        normalized = normalize_price(price)
        prices = self.week(start).setdefault('prices', {})
        if normalized is None:
            prices.pop(key, None)
        else:
            prices[key] = normalized
        self.save()

    def remove_item(self, start: str, key: str) -> None:
        state = self.week(start)
        state.setdefault('prices', {}).pop(key, None)
        custom = state['custom']
        state['custom'] = [item for item in custom if item_key(item) != key]
        if len(state['custom']) == len(custom) and key not in state['excluded']:
            state['excluded'].append(key)
        self.save()

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
        self.weeks[start] = {'plans': [], 'excludedPlans': [str(plan['id']) for plan in (plans or [])],
                             'excluded': [], 'custom': [], 'checked': [], 'prices': {}}
        self.save()

    def items(self, start: str, plans: list[dict], recipes: list[dict]) -> list[dict]:
        state = self.week(start)
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
        for item in state['custom']:
            combined[item_key(item)] = {**item, 'amount': Decimal(str(item['amount']))}
        return sorted((item for key, item in combined.items() if key not in state['excluded']),
                      key=lambda item: item['name'].casefold())
