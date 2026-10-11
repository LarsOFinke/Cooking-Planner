import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cooking_planner.api.backend import BackendLauncher


class BackendLauncherTest(unittest.TestCase):
    def test_frozen_app_uses_bundled_jar_and_java(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            data = Path(temp) / "data"
            java = bundle / "runtime" / "bin" / ("java.exe" if sys.platform == "win32" else "java")
            java.parent.mkdir(parents=True)
            java.touch()
            (bundle / "backend.jar").touch()
            (bundle / "catalogs").mkdir()
            process = MagicMock()
            process.poll.return_value = None
            launcher = BackendLauncher(8765, data)
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(bundle), create=True), \
                 patch("cooking_planner.api.backend.socket.create_connection", side_effect=ConnectionRefusedError), \
                 patch.object(launcher, "_healthy", return_value=True), \
                 patch("cooking_planner.api.backend.subprocess.Popen", return_value=process) as popen:
                try:
                    launcher.start()
                    self.assertEqual([str(java), "-jar", str(bundle / "backend.jar")], popen.call_args.args[0])
                    self.assertEqual(str(bundle / "catalogs"), popen.call_args.kwargs["env"]["COOKING_PLANNER_CATALOG_DIR"])
                    self.assertEqual(launcher.instance_token, popen.call_args.kwargs["env"]["COOKING_PLANNER_INSTANCE_TOKEN"])
                finally:
                    launcher.stop()

    def test_occupied_port_is_rejected_before_starting_backend(self):
        launcher = BackendLauncher(8765, Path('/tmp/cooking-planner-test-data'))
        with patch('cooking_planner.api.backend.socket.create_connection') as connect, \
             patch('cooking_planner.api.backend.subprocess.Popen') as popen:
            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                launcher.start()
            connect.assert_called_once()
            popen.assert_not_called()

    def test_health_requires_matching_instance_token(self):
        launcher = BackendLauncher(8765, Path('/tmp/cooking-planner-test-data'))
        for token, expected in (('other-instance', False), (launcher.instance_token, True)):
            response = io.BytesIO(json.dumps({'status': 'ok', 'instanceToken': token}).encode())
            response.status = 200
            with patch('cooking_planner.api.backend.urlopen', return_value=response):
                self.assertEqual(expected, launcher._healthy())


if __name__ == "__main__":
    unittest.main()
