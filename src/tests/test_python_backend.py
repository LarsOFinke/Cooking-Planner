import json
import sqlite3
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from fastapi.testclient import TestClient

from cooking_planner_backend.app import create_app
from cooking_planner_backend.recipes.mapper import map_recipe
from cooking_planner_backend.entities.marker import Marker


ROOT = Path(__file__).resolve().parents[2]


class PythonBackendTest(unittest.TestCase):
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
        self._open()

    def _open(self):
        self.app = create_app(self.data, self.catalogs, 'test-token')
        self.client = TestClient(self.app)
        self.addCleanup(self.app.state.storage.close)

    def test_catalogs_locales_and_plan_shopping_survive_reopen(self):
        self.assertEqual(['de', 'en'], self.client.get('/api/recipes/locales').json())
        self.assertEqual(2, self.client.get('/api/recipes/info?locale=en').json()['recipeCount'])
        recipe_id = self.rows['en']['id']
        first = self.client.get(f'/api/recipes/{recipe_id}?locale=en').json()
        german = self.client.get(f'/api/recipes/{recipe_id}?locale=de').json()
        self.assertEqual(recipe_id, german['id'])
        self.assertNotEqual(first['name'], german['name'])
        response = self.client.put('/api/plans', json={'date': '2026-10-12', 'mealType': 'LUNCH',
            'recipeId': recipe_id, 'servings': 2})
        self.assertEqual(200, response.status_code, response.text)
        plan = response.json()
        self.assertEqual(2, plan['servings'])
        self.assertEqual(german['name'], self.client.get(
            '/api/plans?from=2026-10-12&to=2026-10-18&locale=de').json()[0]['recipeTitle'])
        shopping = self.client.get('/api/plans/shopping?from=2026-10-12&to=2026-10-18&locale=en').json()
        first_ingredient = first['ingredients'][0]
        item = next(item for item in shopping if item['ingredientId'] == first_ingredient['ingredientId'])
        self.assertEqual(first_ingredient['amount'] * 2, item['amount'])
        self.assertEqual(1, item['recipeCount'])
        self._open()
        self.assertEqual(plan['id'], self.client.get(
            '/api/plans?from=2026-10-12&to=2026-10-18&locale=en').json()[0]['id'])
        self.assertEqual(400, self.client.get('/api/plans?from=2026-10-18&to=2026-10-12').status_code)
        self.assertEqual(400, self.client.put('/api/plans', json={'date': 'bad', 'mealType': 'LUNCH',
            'recipeId': recipe_id, 'servings': 2}).status_code)
        self.assertEqual(204, self.client.delete(f'/api/plans/{plan["id"]}').status_code)

    def test_optional_catalog_labels_are_strings_for_browser_search(self):
        row = deepcopy(self.rows['en'])
        for key in ('country', 'region', 'continent', 'category_label', 'difficulty_label',
                    'effort_label', 'diet_type_label', 'data_source_label'):
            row[key] = None
        dto = map_recipe(row, 'en', {})
        for key in ('country', 'region', 'continent', 'categoryLabel', 'difficultyLabel',
                    'effortLabel', 'dietTypeLabel', 'dataSourceLabel'):
            self.assertEqual('', dto[key])

    def test_ingredient_catalog_and_prices(self):
        item = self.rows['en']['ingredients'][0]
        ingredient_id = item['ingredient_id']
        matches = self.client.get('/api/ingredients', params={'locale': 'en', 'q': item['name'][:3]}).json()
        self.assertIn(ingredient_id, {match['id'] for match in matches})
        self.assertEqual(200, self.client.put(f'/api/admin/ingredients/{ingredient_id}', json={
            'translations': {'en': 'Updated ingredient', 'de': 'Neue Zutat'}}).status_code)
        recipe = self.client.get(f'/api/recipes/{self.rows["en"]["id"]}?locale=en').json()
        self.assertEqual('Updated ingredient', recipe['ingredients'][0]['name'])
        self.assertEqual(409, self.client.delete(f'/api/admin/ingredients/{ingredient_id}').status_code)
        self.assertEqual(200, self.client.put(f'/api/ingredients/{ingredient_id}/reference-prices?unit=g',
            json={'price': '1.80', 'basisQuantity': 100}).status_code)
        self.assertEqual('1.80', self.client.get('/api/ingredients/reference-prices').json()[f'{ingredient_id}:g']['price'])
        self.assertEqual(200, self.client.put(f'/api/ingredients/{ingredient_id}/prices?week=2026-10-12&unit=g',
            json={'price': '2.50'}).status_code)
        self.assertEqual('2.50', self.client.get('/api/ingredients/prices?week=2026-10-12').json()[f'{ingredient_id}:g'])
        self.assertEqual(400, self.client.put(f'/api/ingredients/{ingredient_id}/prices?week=bad&unit=g',
            json={'price': '2.50'}).status_code)
        self.assertEqual(204, self.client.delete('/api/ingredients/prices?week=2026-10-12').status_code)
        self.assertEqual({}, self.client.get('/api/ingredients/prices?week=2026-10-12').json())

    def test_recipe_admin_overlay_and_omission_preserve_base_catalog(self):
        source = deepcopy(self.rows['en'])
        source['id'] = 'custom-dish'
        source['name'] = 'Custom dish'
        source['image_folder'] = 'recipe_images/custom-dish'
        source['images'] = []
        response = self.client.post('/api/admin/recipes/custom-dish', json={
            'sourceLocale': 'en', 'translations': {'en': source, 'de': None}})
        self.assertEqual(201, response.status_code, response.text)
        self.assertEqual(3, len(self.client.get('/api/recipes?locale=en').json()))
        self.assertEqual(2, len(self.client.get('/api/recipes?locale=de').json()))
        self.assertEqual(409, self.client.post('/api/admin/recipes/custom-dish', json={
            'sourceLocale': 'en', 'translations': {'en': source, 'de': None}}).status_code)
        self.assertEqual(200, self.client.put('/api/plans', json={'date': '2026-10-13', 'mealType': 'DINNER',
            'recipeId': 'custom-dish', 'servings': 1}).status_code)
        self.assertEqual(204, self.client.delete('/api/admin/recipes/custom-dish').status_code)
        self.assertEqual('Missing recipe', self.client.get(
            '/api/plans?from=2026-10-12&to=2026-10-18&locale=en').json()[0]['recipeTitle'])
        self.assertEqual(2, json.loads((self.catalogs / 'recipes_en.json').read_text())['metadata']['recipe_count'])
        self._open()
        self.assertEqual(2, len(self.client.get('/api/recipes?locale=en').json()))

    def test_legacy_price_import_does_not_modify_shopping_file(self):
        key = self.rows['en']['ingredients'][0]['ingredient_id'] + ':g'
        shopping = {'version': 1, 'weeks': {'2026-10-12': {'prices': {key: '3.25'}}}}
        original = json.dumps(shopping)
        path = self.data / 'shopping.json'
        path.write_text(original)
        self.app.state.storage.close()
        (self.data / 'cooking-planner.db').unlink()
        self._open()
        self.assertEqual('3.25', self.client.get('/api/ingredients/prices?week=2026-10-12').json()[key])
        self.assertEqual(original, path.read_text())

    def test_old_sqlite_price_schema_is_upgraded_without_losing_rows(self):
        self.app.state.storage.close()
        database = self.data / 'cooking-planner.db'
        database.unlink()
        ingredient_id = self.rows['en']['ingredients'][0]['ingredient_id']
        with sqlite3.connect(database) as connection:
            connection.executescript('''
                CREATE TABLE ingredient (id TEXT PRIMARY KEY);
                CREATE TABLE ingredient_price (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ingredient_id TEXT NOT NULL, week_start TEXT NOT NULL, unit TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL, UNIQUE(ingredient_id, week_start, unit));
            ''')
            connection.execute('INSERT INTO ingredient(id) VALUES (?)', (ingredient_id,))
            connection.execute('INSERT INTO ingredient_price(ingredient_id, week_start, unit, amount_cents)'
                               ' VALUES (?, ?, ?, ?)', (ingredient_id, '2026-10-12', 'g', 275))
        self._open()
        key = f'{ingredient_id}:g'
        self.assertEqual('2.75', self.client.get('/api/ingredients/prices?week=2026-10-12').json()[key])
        with sqlite3.connect(database) as connection:
            columns = {row[1] for row in connection.execute('PRAGMA table_info(ingredient_price)')}
        self.assertIn('basis_quantity', columns)

    def test_recipe_edit_journal_recovers_committed_and_rolled_back_file(self):
        before = {'version': 1, 'upserts': {}, 'deleted': []}
        after = {'version': 1, 'upserts': {}, 'deleted': [self.rows['en']['id']]}
        edit = self.data / 'recipe-edits.json'
        pending = self.data / 'recipe-edits.pending.json'
        self.app.state.storage.close()
        edit.write_text(json.dumps(after))
        pending.write_text(json.dumps({'marker': 'recipe-edit-not-committed',
                                       'before': before, 'after': after}))
        self._open()
        self.assertEqual(before, json.loads(edit.read_text()))
        self.assertFalse(pending.exists())
        with self.app.state.storage.session() as session:
            session.add(Marker(name='recipe-edit-committed'))
        pending.write_text(json.dumps({'marker': 'recipe-edit-committed',
                                       'before': before, 'after': after}))
        self.app.state.storage.close()
        self._open()
        self.assertEqual(after, json.loads(edit.read_text()))
        self.assertEqual(1, len(self.client.get('/api/recipes?locale=en').json()))


if __name__ == '__main__':
    unittest.main()
