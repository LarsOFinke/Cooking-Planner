"""Validate and atomically store a shopping draft without replacing invalid data."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from cooking_planner.pricing import normalize_price


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


def valid_pending(operation: object) -> bool:
    if not isinstance(operation, dict):
        return False
    required = {'ingredient': ('id', 'name', 'locale'),
                'price': ('week', 'key', 'price'), 'clear_prices': ('week',)}
    fields = required.get(operation.get('kind'))
    return fields is not None and all(isinstance(operation.get(field), str) for field in fields)


def load_draft(path: Path) -> tuple[dict, list, str | None]:
    if not path.is_file():
        return {}, [], None
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(document, dict) or document.get('version') != 1
                or not isinstance(document.get('weeks'), dict)
                or not isinstance(document.get('pending', []), list)
                or any(not valid_pending(operation) for operation in document.get('pending', []))
                or any(not isinstance(week, str) or not valid_week(state)
                       for week, state in document['weeks'].items())):
            raise ValueError('Unsupported shopping draft format')
        return document['weeks'], document.get('pending', []), None
    except (ValueError, TypeError, AttributeError):
        backup = path.with_name(f'{path.name}.invalid-{uuid4().hex}.bak')
        with path.open('rb') as source, backup.open('xb') as destination:
            copyfileobj(source, destination)
        return {}, [], f'Shopping draft could not be read. Original saved to {backup}'


def save_draft(path: Path, weeks: dict, pending: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'version': 1, 'weeks': weeks, 'pending': pending},
                                    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
