import io
import json
import os
import sys
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.api.ApiClient import ApiClient
from cooking_planner.api.local_http import open_local


class ApiClientTest(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient('http://127.0.0.1:8765/', 'test-token')

    def test_local_requests_ignore_inherited_http_proxy(self):
        class Backend(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'["de"]')

            def log_message(self, *_):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Backend) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                proxy = 'http://127.0.0.1:1'
                with patch.dict(os.environ, {'http_proxy': proxy, 'HTTP_PROXY': proxy,
                                             'no_proxy': '', 'NO_PROXY': ''}):
                    client = ApiClient(f'http://127.0.0.1:{server.server_port}', 'test-token')
                    self.assertEqual(['de'], client.locales())
            finally:
                server.shutdown()
                thread.join(timeout=2)

    def test_local_transport_rejects_external_host(self):
        with self.assertRaisesRegex(ValueError, '127.0.0.1'):
            open_local(Request('http://example.invalid/'), timeout=1)

    def test_local_transport_does_not_follow_redirects(self):
        class RedirectingBackend(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header('Location', 'http://127.0.0.1:1/steal')
                self.end_headers()

            def log_message(self, *_):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), RedirectingBackend) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                client = ApiClient(f'http://127.0.0.1:{server.server_port}', 'test-token')
                with self.assertRaisesRegex(RuntimeError, r'Request failed \(302\)'):
                    client.locales()
            finally:
                server.shutdown()
                thread.join(timeout=2)

    def test_locale_and_shopping_queries_are_encoded(self):
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'["de","en"]'
            self.assertEqual(['de', 'en'], self.client.locales())
            request = open_url.call_args.args[0]
            self.assertEqual('http://127.0.0.1:8765/api/recipes/locales', request.full_url)
            self.assertEqual('test-token', request.get_header('X-cooking-planner-token'))
            open_url.return_value.__enter__.return_value.read.return_value = b'[]'
            self.assertEqual([], self.client.shopping('2026-10-10', '2026-10-16', 'de'))
            self.assertIn('locale=de', open_url.call_args.args[0].full_url)

    def test_save_plan_sends_json_with_stable_recipe_id(self):
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"id":7}'
            result = self.client.save_plan('2026-10-10', 'DINNER', 'dz-algerischer-couscous', 3)
            request = open_url.call_args.args[0]
            self.assertEqual('PUT', request.get_method())
            self.assertEqual({'date': '2026-10-10', 'mealType': 'DINNER',
                              'recipeId': 'dz-algerischer-couscous', 'servings': 3},
                             json.loads(request.data))
            self.assertEqual({'id': 7}, result)

    def test_empty_delete_and_useful_connection_errors(self):
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
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
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
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
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"en":{"category":[]}}'
            self.assertEqual({'en': {'category': []}}, self.client.admin_options())
            self.assertEqual('http://127.0.0.1:8765/api/admin/recipes/options',
                             open_url.call_args.args[0].full_url)

    def test_ingredient_admin_sends_localized_names(self):
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"id":"rice"}'
            self.client.save_admin_ingredient('rice', {'en': 'Rice', 'de': 'Reis'})
            request = open_url.call_args.args[0]
            self.assertEqual('PUT', request.get_method())
            self.assertEqual({'translations': {'en': 'Rice', 'de': 'Reis'}}, json.loads(request.data))
            open_url.return_value.__enter__.return_value.read.return_value = b'[]'
            self.client.admin_ingredients('grün')
            self.assertIn('q=gr%C3%BCn', open_url.call_args.args[0].full_url)

    def test_reference_price_sends_quantity_basis(self):
        with patch('cooking_planner.api.ApiClient.open_local') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b''
            self.client.save_reference_price('rice:g', '1.80', 100)
            request = open_url.call_args.args[0]
            self.assertEqual('PUT', request.get_method())
            self.assertTrue(request.full_url.endswith('/api/ingredients/rice/reference-prices?unit=g'))
            self.assertEqual({'price': '1.80', 'basisQuantity': 100}, json.loads(request.data))


if __name__ == '__main__':
    unittest.main()
