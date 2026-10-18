"""Exercise local operations against real catalogs, SQLite, and user files."""

import base64
import json
import socket
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner_backend.core.ConflictError import ConflictError
from cooking_planner_backend.core.LocalPlanner import LocalPlanner
from cooking_planner_backend.entities.Marker import Marker
from cooking_planner_backend.stores.recipe_mapper import map_recipe

ROOT = Path(__file__).resolve().parents[2]
START = '2026-10-12'
END = '2026-10-18'


class LocalPlannerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalogs = self.root / 'catalogs'
        self.catalogs.mkdir()
        self.rows = {}
        for locale in ('en', 'de'):
            document = json.loads((ROOT / 'data' / f'recipes_{locale}.json').read_text(encoding='utf-8'))
            document['recipes'] = document['recipes'][:2]
            document['metadata']['recipe_count'] = 2
            (self.catalogs / f'recipes_{locale}.json').write_text(json.dumps(document), encoding='utf-8')
            self.rows[locale] = document['recipes'][0]
        self.data = self.root / 'user'
        self.data.mkdir()
        self.client = None
        self.addCleanup(lambda: self.client.close() if self.client else None)
        self._open()

    def _open(self):
        if self.client:
            self.client.close()
        self.client = LocalPlanner(self.data, self.catalogs)

    def source(self, recipe_id, name=None):
        source = deepcopy(self.rows['en'])
        source['id'] = recipe_id
        source['name'] = name or source['name']
        source['image_folder'] = f'recipe_images/{recipe_id}'
        source['images'] = []
        return source

    def test_local_operations_do_not_open_a_network_connection(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network opened')):
            self.assertEqual(['de', 'en'], self.client.locales())
            self.assertEqual(2, self.client.catalog_info('en')['recipeCount'])
            self.client.save_plan(START, 'LUNCH', self.rows['en']['id'], 2)
            self.assertEqual(1, len(self.client.plans(START, END, 'en')))

    def test_catalogs_and_plan_survive_reopen(self):
        info = self.client.catalog_info('en')
        self.assertEqual(2, info['recipeCount'])
        self.assertGreater(info['categoryCount'], 0)
        recipe_id = self.rows['en']['id']
        first = self.client.recipes('en')[0]
        german = self.client.recipe_store.get('de', recipe_id)
        self.assertNotEqual(first['name'], german['name'])
        plan = self.client.save_plan(START, 'LUNCH', recipe_id, 2)
        self.assertEqual(german['name'], self.client.plans(START, END, 'de')[0]['recipeTitle'])
        self._open()
        self.assertEqual(plan['id'], self.client.plans(START, END, 'en')[0]['id'])
        with self.assertRaisesRegex(ValueError, 'Date range'):
            self.client.plans(END, START, 'en')
        with self.assertRaisesRegex(ValueError, 'ISO date'):
            self.client.save_plan('bad', 'LUNCH', recipe_id, 2)
        self.client.delete_plan(plan['id'])
        self.assertEqual([], self.client.plans(START, END, 'en'))

    def test_ui_recipe_rows_do_not_share_mutable_catalog_lists(self):
        row = deepcopy(self.rows['en'])
        for key in ('country', 'region', 'continent', 'category_label', 'difficulty_label',
                    'effort_label', 'diet_type_label', 'data_source_label'):
            row[key] = None
        dto = map_recipe(row, 'en', {})
        for key in ('country', 'region', 'continent', 'categoryLabel', 'difficultyLabel',
                    'effortLabel', 'dietTypeLabel', 'dataSourceLabel'):
            self.assertEqual('', dto[key])
        dto['images'].append('other.png')
        dto['suitableFor'].append('other')
        dto['instructions'][0]['ingredientIds'].append('other')
        self.assertNotIn('other.png', row['images'])
        self.assertNotIn('other', row['suitable_for'])
        self.assertNotIn('other', row['instructions']['steps'][0]['ingredient_ids'])

    def test_ingredient_catalog_and_prices(self):
        item = self.rows['en']['ingredients'][0]
        ingredient_id = item['ingredient_id']
        matches = self.client.ingredients('en', item['name'][:3])
        self.assertIn(ingredient_id, {match['id'] for match in matches})
        self.client.save_admin_ingredient(ingredient_id, {'en': 'Updated ingredient', 'de': 'Neue Zutat'})
        recipe = self.client.recipe_store.get('en', self.rows['en']['id'])
        self.assertEqual('Updated ingredient', recipe['ingredients'][0]['name'])
        with self.assertRaises(ConflictError):
            self.client.delete_admin_ingredient(ingredient_id)
        key = f'{ingredient_id}:g'
        self.client.save_reference_price(key, '1.80', 100)
        self.assertEqual('1.80', self.client.reference_prices()[key]['price'])
        self.client.save_ingredient_price(START, key, '2.50')
        self.assertEqual('2.50', self.client.ingredient_prices(START)[key])
        with self.assertRaisesRegex(ValueError, 'ISO date'):
            self.client.save_ingredient_price('bad', key, '2.50')
        self.client.clear_ingredient_prices(START)
        self.assertEqual({}, self.client.ingredient_prices(START))

    def test_recipe_admin_overlay_and_omission_preserve_catalog(self):
        source = self.source('custom-dish', 'Custom dish')
        self.client.save_recipe('custom-dish', 'en', {'en': source, 'de': None}, True)
        self.assertEqual(3, len(self.client.recipes('en')))
        self.assertEqual(2, len(self.client.recipes('de')))
        with self.assertRaises(ConflictError):
            self.client.save_recipe('custom-dish', 'en', {'en': source, 'de': None}, True)
        self.client.save_plan('2026-10-13', 'DINNER', 'custom-dish', 1)
        self.client.delete_recipe('custom-dish')
        self.assertEqual('Missing recipe', self.client.plans(START, END, 'en')[0]['recipeTitle'])
        self.assertEqual(2, json.loads((self.catalogs / 'recipes_en.json').read_text())['metadata']['recipe_count'])
        self._open()
        self.assertEqual(2, len(self.client.recipes('en')))

    def test_recipe_save_requires_catalog_ingredients_and_keeps_names(self):
        source = self.source('catalog-only-dish', 'Catalog only dish')
        original_id = source['ingredients'][0]['ingredient_id']
        source['ingredients'][0]['ingredient_id'] = 'unknown-ingredient'
        for step in source['instructions']['steps']:
            step['ingredient_ids'] = ['unknown-ingredient' if item == original_id else item
                                      for item in step['ingredient_ids']]
        with self.assertRaisesRegex(ValueError, 'existing ingredients'):
            self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, True)
        source['ingredients'][0]['ingredient_id'] = original_id
        for step in source['instructions']['steps']:
            step['ingredient_ids'] = [original_id if item == 'unknown-ingredient' else item
                                      for item in step['ingredient_ids']]
        source['ingredients'][0]['name'] = 'Forged ingredient name'
        self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, True)
        edits = json.loads((self.data / 'recipe-edits.json').read_text())
        self.assertEqual(self.rows['en']['ingredients'][0]['name'],
                         edits['upserts'][source['id']]['en']['ingredients'][0]['name'])

    def test_recipe_images_use_private_data_and_reject_duplicate_bytes(self):
        source = self.source('country-dish', 'Country dish')
        source['images'] = ['recipe_images/country-dish/image_01-aaaaaaaaaaaa.png']
        photo = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==')
        self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, True,
                                [{'reference': source['images'][0], 'data': photo}])
        saved = self.data / 'recipe_images/country-dish/image_01-aaaaaaaaaaaa.png'
        self.assertEqual(photo, saved.read_bytes())
        self.assertFalse((self.catalogs / 'recipe_images/country-dish').exists())
        duplicate = 'recipe_images/country-dish/image_02-bbbbbbbbbbbb.png'
        source['images'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'same image'):
            self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, False,
                                    [{'reference': duplicate, 'data': photo}])
        self.assertFalse((self.data / 'recipe_images/country-dish/image_02-bbbbbbbbbbbb.png').exists())
        self.assertEqual([source['images'][0]], self.client.admin_recipe(source['id'])['translations']['en']['images'])
        source['images'] = []
        self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, False, [])
        self.assertFalse(saved.exists())

    def test_recipe_duplicate_uses_name_and_origin(self):
        source = self.source('same-dish-other-origin')
        with self.assertRaises(ConflictError):
            self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, True)
        self.assertFalse((self.data / 'recipe-edits.json').exists())
        source['country_code'] = 'zz'
        source['country'] = 'Another country'
        self.client.save_recipe(source['id'], 'en', {'en': source, 'de': None}, True)

    def test_legacy_price_import_preserves_shopping_file(self):
        key = self.rows['en']['ingredients'][0]['ingredient_id'] + ':g'
        shopping = {'version': 1, 'weeks': {START: {'prices': {key: '3.25'}}}}
        original = json.dumps(shopping)
        path = self.data / 'shopping.json'
        path.write_text(original)
        self.client.close()
        (self.data / 'cooking-planner.db').unlink()
        self._open()
        self.assertEqual('3.25', self.client.ingredient_prices(START)[key])
        self.assertEqual(original, path.read_text())

    def test_old_sqlite_price_schema_is_upgraded_without_losing_rows(self):
        self.client.close()
        database = self.data / 'cooking-planner.db'
        database.unlink()
        ingredient_id = self.rows['en']['ingredients'][0]['ingredient_id']
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript('''
                CREATE TABLE ingredient (id TEXT PRIMARY KEY);
                CREATE TABLE ingredient_price (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ingredient_id TEXT NOT NULL, week_start TEXT NOT NULL, unit TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL, UNIQUE(ingredient_id, week_start, unit));
            ''')
            connection.execute('INSERT INTO ingredient(id) VALUES (?)', (ingredient_id,))
            connection.execute('INSERT INTO ingredient_price(ingredient_id, week_start, unit, amount_cents)'
                               ' VALUES (?, ?, ?, ?)', (ingredient_id, START, 'g', 275))
            connection.commit()
        self._open()
        key = f'{ingredient_id}:g'
        self.assertEqual('2.75', self.client.ingredient_prices(START)[key])
        with closing(sqlite3.connect(database)) as connection:
            columns = {row[1] for row in connection.execute('PRAGMA table_info(ingredient_price)')}
        self.assertIn('basis_quantity', columns)

    def test_recipe_edit_journal_recovers_both_outcomes(self):
        before = {'version': 1, 'upserts': {}, 'deleted': []}
        after = {'version': 1, 'upserts': {}, 'deleted': [self.rows['en']['id']]}
        edit = self.data / 'recipe-edits.json'
        pending = self.data / 'recipe-edits.pending.json'
        self.client.close()
        edit.write_text(json.dumps(after))
        pending.write_text(json.dumps({'marker': 'recipe-edit-not-committed',
                                       'before': before, 'after': after}))
        self._open()
        self.assertEqual(before, json.loads(edit.read_text()))
        self.assertFalse(pending.exists())
        with self.client.storage.session() as session:
            session.add(Marker(name='recipe-edit-committed'))
        pending.write_text(json.dumps({'marker': 'recipe-edit-committed',
                                       'before': before, 'after': after}))
        self._open()
        self.assertEqual(after, json.loads(edit.read_text()))
        self.assertEqual(1, len(self.client.recipes('en')))


if __name__ == '__main__':
    unittest.main()
