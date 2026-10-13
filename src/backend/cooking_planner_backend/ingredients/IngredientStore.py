"""Ingredient translations and reusable or legacy weekly prices."""

from datetime import date
from decimal import Decimal, InvalidOperation
import logging

from sqlalchemy import func, select

from cooking_planner_backend.recipes.RecipeStore import ID
from cooking_planner_backend.entities.Ingredient import Ingredient
from cooking_planner_backend.entities.Marker import Marker
from cooking_planner_backend.entities.Price import Price
from cooking_planner_backend.entities.Translation import Translation
from cooking_planner_backend.ConflictError import ConflictError
from cooking_planner_backend.repositories.json_files import read_json


log = logging.getLogger(__name__)


def _week(value):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError('Week must be an ISO date') from error


def _key(ingredient_id, unit):
    if (not isinstance(ingredient_id, str) or len(ingredient_id) > 120 or not ID.fullmatch(ingredient_id) or
            not isinstance(unit, str) or not unit.isalpha() or not unit.islower() or len(unit) > 24):
        raise ValueError('Valid ingredient ID and unit are required')


def _cents(raw):
    try:
        value = Decimal(raw.strip().replace(',', '.'))
    except (AttributeError, InvalidOperation) as error:
        raise ValueError('Price must be a non-negative euro amount with at most two decimals') from error
    if not value.is_finite() or value < 0 or value > 1_000_000 or value.as_tuple().exponent < -2:
        raise ValueError('Price must be a non-negative euro amount with at most two decimals')
    return int(value * 100)


def _price(cents):
    return f'{cents / 100:.2f}'


class IngredientStore:
    def __init__(self, storage, recipes):
        self.storage = storage
        self.recipes = recipes
        self._import_legacy_prices()

    def _import_legacy_prices(self):
        try:
            with self.storage.session() as session:
                if session.get(Marker, 'shopping-prices-v1') is not None:
                    return
            document = read_json(self.storage.data_dir / 'shopping.json', None)
            imported = []
            if document is not None:
                if document.get('version') != 1 or not isinstance(document.get('weeks'), dict):
                    raise ValueError('Unsupported shopping draft')
                for week, state in document['weeks'].items():
                    _week(week)
                    for key, value in state.get('prices', {}).items():
                        ingredient_id, unit = key.rsplit(':', 1)
                        _key(ingredient_id, unit)
                        imported.append((ingredient_id, week, unit, _cents(value)))
            with self.storage.session() as session:
                for ingredient_id, week, unit, cents in imported:
                    if session.get(Ingredient, ingredient_id) is None:
                        session.add(Ingredient(id=ingredient_id))
                    existing = session.scalar(select(Price).where(
                        Price.ingredient_id == ingredient_id, Price.week_start == week, Price.unit == unit))
                    if existing is None:
                        session.add(Price(ingredient_id=ingredient_id, week_start=week, unit=unit,
                                          amount_cents=cents))
                session.add(Marker(name='shopping-prices-v1'))
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            log.warning('Could not import legacy shopping prices; shopping.json was left unchanged: %s', error)

    def search(self, locale, query):
        if not query or not query.strip():
            return []
        with self.storage.session() as session:
            found = list(session.scalars(select(Translation).where(
                Translation.locale == locale, func.lower(Translation.name).contains(query.strip().lower()))
                .order_by(Translation.name).limit(40)))
            ids = [row.ingredient_id for row in found]
            names = {}
            if ids:
                for row in session.scalars(select(Translation).where(Translation.ingredient_id.in_(ids))):
                    names.setdefault(row.ingredient_id, {})[row.locale] = row.name
            return [{'id': row.ingredient_id, 'name': row.name,
                     'translations': names[row.ingredient_id]} for row in found]

    def create(self, ingredient_id, locale, name):
        if (not isinstance(ingredient_id, str) or len(ingredient_id) > 120 or not ID.fullmatch(ingredient_id) or
                locale not in self.recipes.locales() or not isinstance(name, str) or
                not name.strip() or len(name) > 180):
            raise ValueError('Valid ingredient ID, language and name are required')
        with self.storage.session() as session:
            if session.get(Ingredient, ingredient_id) is None:
                session.add(Ingredient(id=ingredient_id))
            existing = session.scalar(select(Translation).where(
                Translation.ingredient_id == ingredient_id, Translation.locale == locale))
            if existing is not None and existing.name != name.strip():
                raise ConflictError('Ingredient ID already has a different name')
            if existing is None:
                session.add(Translation(ingredient_id=ingredient_id, locale=locale, name=name.strip()))
        return {'id': ingredient_id, 'name': name.strip(), 'translations': {locale: name.strip()}}

    def catalog(self, query=''):
        with self.storage.session() as session:
            entries = {row.id: {} for row in session.scalars(select(Ingredient))}
            for row in session.scalars(select(Translation)):
                entries.setdefault(row.ingredient_id, {})[row.locale] = row.name
        needle = query.strip().casefold()
        return [{'id': ingredient_id, 'translations': names} for ingredient_id, names in sorted(entries.items())
                if not needle or needle in ingredient_id.casefold() or
                any(needle in name.casefold() for name in names.values())]

    def catalog_entry(self, ingredient_id):
        with self.storage.session() as session:
            if session.get(Ingredient, ingredient_id) is None:
                raise LookupError('Ingredient not found')
            return {'id': ingredient_id, 'translations': {row.locale: row.name for row in session.scalars(
                select(Translation).where(Translation.ingredient_id == ingredient_id))}}

    def _used_in_recipes(self, ingredient_id, locale):
        return any(item.get('ingredient_id') == ingredient_id
                   for recipe in self.recipes.raw_all(locale) for item in recipe['ingredients'])

    def save_catalog_entry(self, ingredient_id, names):
        if not isinstance(ingredient_id, str) or len(ingredient_id) > 120 or not ID.fullmatch(ingredient_id):
            raise ValueError('Valid ingredient ID is required')
        locales = self.recipes.locales()
        if not isinstance(names, dict) or not set(names).issubset(locales):
            raise ValueError('Invalid ingredient translations')
        requested = {locale: (names.get(locale) or '').strip() for locale in locales}
        if not any(requested.values()) or any(len(name) > 180 for name in requested.values()):
            raise ValueError('At least one translated name is required')
        for locale in locales:
            if not requested[locale] and self._used_in_recipes(ingredient_id, locale):
                raise ConflictError(f'Translation is used by recipes in {locale}')
        with self.storage.session() as session:
            if session.get(Ingredient, ingredient_id) is None:
                session.add(Ingredient(id=ingredient_id))
            for locale, name in requested.items():
                existing = session.scalar(select(Translation).where(
                    Translation.ingredient_id == ingredient_id, Translation.locale == locale))
                if name and existing is None:
                    session.add(Translation(ingredient_id=ingredient_id, locale=locale, name=name))
                elif name:
                    existing.name = name
                elif existing is not None:
                    session.delete(existing)
        return self.catalog_entry(ingredient_id)

    def delete_catalog_entry(self, ingredient_id):
        with self.storage.session() as session:
            if session.get(Ingredient, ingredient_id) is None:
                raise LookupError('Ingredient not found')
            if (any(self._used_in_recipes(ingredient_id, locale) for locale in self.recipes.locales()) or
                    session.scalar(select(Price.id).where(Price.ingredient_id == ingredient_id)) is not None or
                    self._used_in_shopping(ingredient_id)):
                raise ConflictError('Ingredient is used by a recipe, shopping item, or saved price')
            for row in session.scalars(select(Translation).where(Translation.ingredient_id == ingredient_id)):
                session.delete(row)
            session.delete(session.get(Ingredient, ingredient_id))

    def _used_in_shopping(self, ingredient_id):
        document = read_json(self.storage.data_dir / 'shopping.json', None)
        if document is None:
            return False
        if document.get('version') != 1 or not isinstance(document.get('weeks'), dict):
            raise ConflictError('Shopping draft cannot be checked; ingredient was not deleted')
        return any(item.get('ingredientId') == ingredient_id for state in document['weeks'].values()
                   for item in state.get('custom', []))

    def prices(self, week):
        _week(week)
        with self.storage.session() as session:
            return {f'{row.ingredient_id}:{row.unit}': _price(row.amount_cents)
                    for row in session.scalars(select(Price).where(Price.week_start == week))}

    def reference_prices(self):
        with self.storage.session() as session:
            return {f'{row.ingredient_id}:{row.unit}':
                    {'price': _price(row.amount_cents), 'basisQuantity': row.basis_quantity}
                    for row in session.scalars(select(Price).where(Price.week_start == '*'))}

    def save_price(self, ingredient_id, week, unit, raw, basis=None):
        if week != '*':
            _week(week)
        _key(ingredient_id, unit)
        if week == '*' and raw and (type(basis) is not int or not 0 < basis <= 1_000_000):
            raise ValueError('Price basis must be a positive quantity')
        cents = None if not raw else _cents(raw)
        with self.storage.session() as session:
            existing = session.scalar(select(Price).where(Price.ingredient_id == ingredient_id,
                Price.week_start == week, Price.unit == unit))
            if cents is None:
                if existing is not None:
                    session.delete(existing)
                return
            if session.get(Ingredient, ingredient_id) is None:
                session.add(Ingredient(id=ingredient_id))
            if existing is None:
                session.add(Price(ingredient_id=ingredient_id, week_start=week, unit=unit,
                                  amount_cents=cents, basis_quantity=basis))
            else:
                existing.amount_cents = cents
                existing.basis_quantity = basis

    def clear_prices(self, week):
        _week(week)
        with self.storage.session() as session:
            for row in session.scalars(select(Price).where(Price.week_start == week)):
                session.delete(row)
