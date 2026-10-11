import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cooking_planner.api.client import ApiClient


class ApiClientTest(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient('http://127.0.0.1:8765/')

    def test_locale_and_shopping_queries_are_encoded(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'["de","en"]'
            self.assertEqual(['de', 'en'], self.client.locales())
            request = open_url.call_args.args[0]
            self.assertEqual('http://127.0.0.1:8765/api/recipes/locales', request.full_url)
            open_url.return_value.__enter__.return_value.read.return_value = b'[]'
            self.assertEqual([], self.client.shopping('2026-10-10', '2026-10-16', 'de'))
            self.assertIn('locale=de', open_url.call_args.args[0].full_url)

    def test_save_plan_sends_json_with_stable_recipe_id(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"id":7}'
            result = self.client.save_plan('2026-10-10', 'DINNER', 'dz-algerischer-couscous', 3)
            request = open_url.call_args.args[0]
            self.assertEqual('PUT', request.get_method())
            self.assertEqual({'date': '2026-10-10', 'mealType': 'DINNER',
                              'recipeId': 'dz-algerischer-couscous', 'servings': 3},
                             json.loads(request.data))
            self.assertEqual({'id': 7}, result)

    def test_empty_delete_and_useful_connection_errors(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b''
            self.assertIsNone(self.client.delete_plan(5))
            self.assertEqual('DELETE', open_url.call_args.args[0].get_method())
            open_url.side_effect = URLError('offline')
            with self.assertRaisesRegex(RuntimeError, 'Cannot reach the local backend'):
                self.client.recipes('en')
            open_url.side_effect = HTTPError('http://localhost', 404, 'missing', {}, io.BytesIO())
            with self.assertRaisesRegex(RuntimeError, 'Request failed \\(404\\)'):
                self.client.recipes('en')

    def test_admin_recipe_save_sends_all_language_choices(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"id":"new-dish"}'
            result = self.client.save_recipe('new-dish', 'en', {'en': {'name': 'New dish'}, 'de': None}, True)
            request = open_url.call_args.args[0]
            self.assertEqual('POST', request.get_method())
            self.assertEqual('http://127.0.0.1:8765/api/admin/recipes/new-dish', request.full_url)
            self.assertEqual({'sourceLocale': 'en', 'translations': {'en': {'name': 'New dish'}, 'de': None}},
                             json.loads(request.data))
            self.assertEqual({'id': 'new-dish'}, result)
            open_url.side_effect = HTTPError('http://localhost', 400, 'bad', {},
                                              io.BytesIO(b'{"message":"Translate ingredient rice for de"}'))
            with self.assertRaisesRegex(RuntimeError, 'Translate ingredient rice for de'):
                self.client.save_recipe('new-dish', 'en', {'en': {}, 'de': {}}, True)

    def test_admin_options_are_loaded_from_backend(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"en":{"category":[]}}'
            self.assertEqual({'en': {'category': []}}, self.client.admin_options())
            self.assertEqual('http://127.0.0.1:8765/api/admin/recipes/options',
                             open_url.call_args.args[0].full_url)

    def test_ingredient_admin_sends_localized_names(self):
        with patch('cooking_planner.api.client.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"id":"rice"}'
            self.client.save_admin_ingredient('rice', {'en': 'Rice', 'de': 'Reis'})
            request = open_url.call_args.args[0]
            self.assertEqual('PUT', request.get_method())
            self.assertEqual({'translations': {'en': 'Rice', 'de': 'Reis'}}, json.loads(request.data))
            open_url.return_value.__enter__.return_value.read.return_value = b'[]'
            self.client.admin_ingredients('grün')
            self.assertIn('q=gr%C3%BCn', open_url.call_args.args[0].full_url)


if __name__ == '__main__':
    unittest.main()
