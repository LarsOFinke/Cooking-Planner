"""Read-only catalogs, user recipe edits, and localized recipe output."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import select

from cooking_planner_backend.entities.Ingredient import Ingredient
from cooking_planner_backend.entities.Marker import Marker
from cooking_planner_backend.entities.Translation import Translation
from cooking_planner_backend.ConflictError import ConflictError
from cooking_planner_backend.recipes.mapper import map_recipe
from cooking_planner_backend.repositories.json_files import read_json, write_json


ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SHARED = ('id', 'country_code', 'region_code', 'continent_code', 'category', 'difficulty',
          'effort', 'data_source', 'prep_minutes', 'cook_minutes', 'total_minutes',
          'diet_type', 'suitable_for', 'image_folder', 'images')
LABELS = {'country_code': 'country', 'region_code': 'region', 'continent_code': 'continent',
          'category': 'category_label', 'difficulty': 'difficulty_label', 'effort': 'effort_label',
          'diet_type': 'diet_type_label', 'data_source': 'data_source_label'}


class RecipeStore:
    def __init__(self, storage, catalog_dir: Path):
        self.storage = storage
        self.catalog_dir = Path(catalog_dir)
        self.edit_path = storage.data_dir / 'recipe-edits.json'
        self.pending_path = storage.data_dir / 'recipe-edits.pending.json'
        self._cache = {}
        self._recover()
        self._seed()

    def locales(self):
        return sorted(path.stem[-2:] for path in self.catalog_dir.glob('recipes_??.json')
                      if re.fullmatch(r'recipes_[a-z]{2}\.json', path.name))

    def _edits(self):
        edits = read_json(self.edit_path, {'version': 1, 'upserts': {}, 'deleted': []})
        if (not isinstance(edits, dict) or edits.get('version') != 1 or
                not isinstance(edits.get('upserts'), dict) or not isinstance(edits.get('deleted'), list)):
            raise ValueError('Unsupported recipe edits file; original was not changed')
        return edits

    def _recover(self):
        pending = read_json(self.pending_path, None)
        if pending is None:
            return
        if not isinstance(pending, dict) or any(key not in pending for key in ('marker', 'before', 'after')):
            raise ValueError('Unsupported pending recipe edit; original was not changed')
        chosen = pending['after'] if self.storage.marker_exists(pending['marker']) else pending['before']
        write_json(self.edit_path, chosen)
        self.pending_path.unlink()

    def _catalog(self, locale):
        if locale not in self.locales():
            raise ValueError(f'Recipe language unavailable: {locale}')
        path = self.catalog_dir / f'recipes_{locale}.json'
        if path.stat().st_size > 8_000_000:
            raise ValueError(f'Recipe catalog is too large: {path}')
        stamp = (path.stat().st_mtime_ns, self.edit_path.stat().st_mtime_ns if self.edit_path.exists() else 0)
        if locale in self._cache and self._cache[locale][0] == stamp:
            return self._cache[locale][1:]
        document = read_json(path, None)
        metadata = document.get('metadata', {}) if isinstance(document, dict) else {}
        rows = document.get('recipes') if isinstance(document, dict) else None
        if (metadata.get('schema_version') not in ('1.1.0', '1.2.0') or
                metadata.get('language') != locale or not isinstance(rows, list) or
                metadata.get('recipe_count') != len(rows)):
            raise ValueError(f'Invalid recipe catalog: {path}')
        result = {}
        for row in rows:
            self._validate_catalog_row(row, result)
            result[row['id']] = row
        edits = self._edits()
        for recipe_id in edits['deleted']:
            result.pop(recipe_id, None)
        for recipe_id, translations in edits['upserts'].items():
            if locale not in translations:
                continue
            row = translations[locale]
            if row is None:
                result.pop(recipe_id, None)
            else:
                if row.get('id') != recipe_id:
                    raise ValueError(f'Recipe edit ID does not match its key: {recipe_id}')
                self._validate_catalog_row(row, {})
                result[recipe_id] = row
        self._cache[locale] = (stamp, metadata, result)
        return metadata, result

    @staticmethod
    def _validate_catalog_row(row, seen):
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str) or
                not isinstance(row.get('name'), str) or not row['name'].strip() or
                not isinstance(row.get('ingredients'), list) or not row['ingredients'] or row['id'] in seen):
            raise ValueError('Invalid or duplicate recipe in catalog')

    def _seed(self):
        names = {}
        for locale in self.locales():
            for row in self._catalog(locale)[1].values():
                for item in row['ingredients']:
                    ingredient_id, name = item.get('ingredient_id'), item.get('name')
                    if ingredient_id and name:
                        names.setdefault((ingredient_id, locale), name)
        with self.storage.session() as session:
            existing_ids = set(session.scalars(select(Ingredient.id)))
            existing_names = set(session.execute(select(Translation.ingredient_id, Translation.locale)))
            for (ingredient_id, locale), name in names.items():
                if ingredient_id not in existing_ids:
                    session.add(Ingredient(id=ingredient_id))
                    existing_ids.add(ingredient_id)
                if (ingredient_id, locale) not in existing_names:
                    session.add(Translation(ingredient_id=ingredient_id, locale=locale, name=name))

    def raw_all(self, locale):
        return list(self._catalog(locale)[1].values())

    def ids(self):
        return sorted({recipe_id for locale in self.locales() for recipe_id in self._catalog(locale)[1]})

    def _names(self, locale):
        with self.storage.session() as session:
            return {row.ingredient_id: row.name for row in session.scalars(
                select(Translation).where(Translation.locale == locale))}

    def list(self, locale):
        names = self._names(locale)
        return [map_recipe(row, locale, names) for row in self.raw_all(locale)]

    def get(self, locale, recipe_id):
        row = self._catalog(locale)[1].get(recipe_id)
        if row is None:
            raise LookupError('Recipe not found')
        return map_recipe(row, locale, self._names(locale))

    def info(self, locale):
        metadata, rows = self._catalog(locale)
        return {'locale': locale, 'dataset': metadata.get('dataset', ''), 'recipeCount': len(rows),
                'categoryCount': len({row.get('category_label') for row in rows.values()
                                      if row.get('category_label')}),
                'countryCount': len({row.get('country_code') for row in rows.values() if row.get('country_code')}),
                'regionCount': len({row.get('region_code') for row in rows.values() if row.get('region_code')}),
                'quantityNote': metadata.get('quantity_note', ''), 'dietNote': metadata.get('diet_note', ''),
                'originNote': metadata.get('origin_note', ''), 'quality': metadata.get('quality', '')}

    def admin_list(self):
        return [{'id': recipe_id, 'names': {locale: row['name'] for locale in self.locales()
                 if (row := self._catalog(locale)[1].get(recipe_id)) is not None}}
                for recipe_id in self.ids()]

    def admin_get(self, recipe_id):
        names = {locale: self._names(locale) for locale in self.locales()}
        translations = {}
        for locale in self.locales():
            row = self._catalog(locale)[1].get(recipe_id)
            if row is not None:
                row = deepcopy(row)
                for ingredient in row['ingredients']:
                    ingredient['name'] = names[locale].get(ingredient['ingredient_id'], ingredient['name'])
            translations[locale] = row
        if all(row is None for row in translations.values()):
            raise LookupError('Recipe not found')
        return {'id': recipe_id, 'translations': translations}

    def options(self):
        result = {}
        for locale in self.locales():
            choices = {key: {} for key in (*LABELS, 'suitable_for')}
            for row in self.raw_all(locale):
                for key, label_key in LABELS.items():
                    code = row.get(key, '')
                    if code:
                        choices[key].setdefault(code, row.get(label_key) or code)
                for index, code in enumerate(row.get('suitable_for', [])):
                    labels = row.get('suitable_for_labels', [])
                    if code:
                        choices['suitable_for'].setdefault(code, labels[index] if index < len(labels) else code)
            result[locale] = {key: [{'value': value, 'label': label} for value, label in
                                    sorted(values.items(), key=lambda item: item[1])]
                              for key, values in choices.items()}
        return result

    def _validate_shared(self, recipe_id, row):
        if any(key not in row or row[key] is None for key in SHARED):
            raise ValueError('Missing shared recipe field')
        if any(not row.get(key) for key in ('category', 'difficulty', 'effort', 'data_source', 'diet_type')):
            raise ValueError('Missing recipe category or classification')
        if any(type(row.get(key)) is not int or not 0 <= row[key] <= 1440
               for key in ('prep_minutes', 'cook_minutes', 'total_minutes')):
            raise ValueError('Recipe times must be between 0 and 1440')
        if (not isinstance(row.get('suitable_for'), list) or not isinstance(row.get('images'), list) or
                row['image_folder'] != f'recipe_images/{recipe_id}' or len(row['images']) > 3):
            raise ValueError('Invalid recipe images or diets')
        if any(not re.fullmatch(rf'recipe_images/{re.escape(recipe_id)}/image_0[1-3]\.(webp|png|jpg|jpeg)', path)
               for path in row['images']):
            raise ValueError('Invalid recipe image path')
        ingredients = row.get('ingredients')
        if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 100:
            raise ValueError('A recipe needs 1 to 100 ingredients')
        ids = set()
        for item in ingredients:
            ingredient_id = item.get('ingredient_id', '')
            try:
                amount = Decimal(str(item.get('amount')))
            except InvalidOperation as error:
                raise ValueError('Invalid ingredient amount') from error
            if (not ID.fullmatch(ingredient_id) or ingredient_id in ids or not amount.is_finite() or
                    amount <= 0 or item.get('unit') not in ('g', 'ml', 'pcs')):
                raise ValueError('Ingredients need unique IDs, positive amounts and g, ml or pcs units')
            ids.add(ingredient_id)
        steps = row.get('instructions', {}).get('steps', [])
        if not isinstance(steps, list) or len(steps) > 50:
            raise ValueError('Instructions must contain up to 50 steps')
        for index, step in enumerate(steps, 1):
            if (step.get('step') != index or not isinstance(step.get('text'), str) or
                    not step['text'].strip() or len(step['text']) > 2000 or
                    not isinstance(step.get('ingredient_ids'), list) or
                    any(ingredient_id not in ids for ingredient_id in step['ingredient_ids'])):
                raise ValueError(f'Invalid instruction step {index}')

    def _synchronize(self, source, translated, locale):
        if not isinstance(translated, dict) or not isinstance(translated.get('name'), str) or not translated['name'].strip():
            raise ValueError(f'Recipe name is required for {locale}')
        row = deepcopy(translated)
        for key in SHARED:
            row[key] = deepcopy(source[key])
        names = {item.get('ingredient_id'): item.get('name', '').strip()
                 for item in translated.get('ingredients', [])}
        row['ingredients'] = []
        for item in source['ingredients']:
            name = names.get(item['ingredient_id'], '')
            if not name or len(name) > 180:
                raise ValueError(f'Translate ingredient {item["ingredient_id"]} for {locale}')
            row['ingredients'].append({**deepcopy(item), 'name': name})
        source_steps = source.get('instructions', {}).get('steps', [])
        target_steps = translated.get('instructions', {}).get('steps', [])
        if len(source_steps) != len(target_steps):
            raise ValueError(f'Translate every instruction step for {locale}')
        row['instructions'] = {'steps': [{**deepcopy(step), 'text': target_steps[index].get('text', '').strip()}
                                         for index, step in enumerate(source_steps)]}
        self._validate_shared(source['id'], row)
        return row

    def save(self, recipe_id, source_locale, translations, create):
        with self.storage.lock:
            if not isinstance(recipe_id, str) or len(recipe_id) > 100 or not ID.fullmatch(recipe_id):
                raise ValueError('Recipe ID must use lowercase letters, numbers and hyphens')
            exists = recipe_id in self.ids()
            old = self._edits()
            if create and (exists or recipe_id in old['deleted']):
                raise ConflictError('Recipe ID already exists or was deleted')
            if not create and not exists:
                raise LookupError('Recipe not found')
            locales = self.locales()
            if source_locale not in locales or not isinstance(translations, dict) or set(translations) != set(locales):
                raise ValueError('Choose a source language and provide every translation or omission')
            source = translations[source_locale]
            if not isinstance(source, dict) or source.get('id') != recipe_id:
                raise ValueError('Source recipe must use the selected recipe ID')
            self._validate_shared(recipe_id, source)
            ingredient_ids = {item['ingredient_id'] for item in source['ingredients']}
            with self.storage.session() as session:
                known_ids = set(session.scalars(select(Ingredient.id).where(Ingredient.id.in_(ingredient_ids))))
                names = {(row.ingredient_id, row.locale): row.name for row in session.scalars(
                    select(Translation).where(Translation.ingredient_id.in_(ingredient_ids)))}
            if known_ids != ingredient_ids:
                raise ValueError('Choose existing ingredients from the ingredient catalog')
            canonical = deepcopy(translations)
            for locale, row in canonical.items():
                if row is None:
                    continue
                for item in row['ingredients']:
                    name = names.get((item['ingredient_id'], locale))
                    if not name:
                        raise ValueError(f'Add ingredient translations in the catalog for {locale}')
                    item['name'] = name
            source = canonical[source_locale]
            rows = {locale: None if canonical[locale] is None else
                    self._synchronize(source, canonical[locale], locale) for locale in locales}
            next_edits = deepcopy(old)
            next_edits['upserts'][recipe_id] = rows
            if recipe_id in next_edits['deleted']:
                next_edits['deleted'].remove(recipe_id)
            marker = 'recipe-edit-' + uuid4().hex
            write_json(self.pending_path, {'marker': marker, 'before': old, 'after': next_edits})
            try:
                write_json(self.edit_path, next_edits)
                with self.storage.session() as session:
                    session.add(Marker(name=marker))
            except BaseException:
                write_json(self.edit_path, old)
                self.pending_path.unlink(missing_ok=True)
                self._cache.clear()
                raise
            self.pending_path.unlink()
            self._cache.clear()
            return self.admin_get(recipe_id)

    def delete(self, recipe_id):
        with self.storage.lock:
            if recipe_id not in self.ids():
                raise LookupError('Recipe not found')
            edits = self._edits()
            edits['upserts'].pop(recipe_id, None)
            if recipe_id not in edits['deleted']:
                edits['deleted'].append(recipe_id)
            write_json(self.edit_path, edits)
            self._cache.clear()
