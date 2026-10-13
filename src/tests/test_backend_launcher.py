import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.api.BackendLauncher import BackendLauncher


class BackendLauncherTest(unittest.TestCase):
    def test_embedded_server_uses_python_backend_and_stops_its_own_thread(self):
        with tempfile.TemporaryDirectory() as temp:
            launcher = BackendLauncher(8765, Path(temp) / 'data')
            catalog = Path(temp) / 'catalogs'
            catalog.mkdir()
            app = MagicMock()
            server = MagicMock()
            server.config.app = app
            thread = MagicMock()
            thread.is_alive.return_value = True
            with patch('cooking_planner.api.BackendLauncher.socket.create_connection', side_effect=ConnectionRefusedError), \
                 patch('cooking_planner.api.BackendLauncher.catalog_directory', return_value=catalog), \
                 patch('cooking_planner.api.BackendLauncher.create_app', return_value=app) as create, \
                 patch('cooking_planner.api.BackendLauncher.uvicorn.Server', return_value=server), \
                 patch('cooking_planner.api.BackendLauncher.Thread', return_value=thread), \
                 patch.object(launcher, '_healthy', return_value=True):
                launcher.start()
                create.assert_called_once_with(launcher.data_dir, catalog, launcher.instance_token)
                thread.start.assert_called_once()
                launcher.stop()
                self.assertTrue(server.should_exit)
                thread.join.assert_called_once_with(timeout=5)
                app.state.storage.close.assert_called_once()

    def test_occupied_port_is_rejected_before_starting_backend(self):
        launcher = BackendLauncher(8765, Path('/tmp/cooking-planner-test-data'))
        with patch('cooking_planner.api.BackendLauncher.socket.create_connection') as connect, \
             patch('cooking_planner.api.BackendLauncher.create_app') as create:
            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                launcher.start()
            connect.assert_called_once()
            create.assert_not_called()

    def test_health_requires_matching_instance_token(self):
        launcher = BackendLauncher(8765, Path('/tmp/cooking-planner-test-data'))
        for token, expected in (('other-instance', False), (launcher.instance_token, True)):
            response = io.BytesIO(json.dumps({'status': 'ok', 'instanceToken': token}).encode())
            response.status = 200
            with patch('cooking_planner.api.BackendLauncher.urlopen', return_value=response):
                self.assertEqual(expected, launcher._healthy())


if __name__ == '__main__':
    unittest.main()
