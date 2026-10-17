"""Small checks for build artifact and dependency selection."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'build' / 'common'))

from wheel_path import wheel_path  # noqa: E402


class BuildScriptTest(unittest.TestCase):
    def test_wheel_selection_requires_one_current_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'pyproject.toml').write_text('[project]\nversion = "1.2.3"\n')
            output = root / 'dist' / 'wheels'
            output.mkdir(parents=True)
            stale = output / 'cooking_planner-1.2.2-py3-none-any.whl'
            stale.touch()
            with self.assertRaisesRegex(ValueError, 'Expected one'):
                wheel_path(root)
            stale.unlink()
            current = output / 'cooking_planner-1.2.3-py3-none-any.whl'
            current.touch()
            self.assertEqual(current, wheel_path(root))
            (output / 'cooking_planner-1.2.3-cp313-none-any.whl').touch()
            with self.assertRaisesRegex(ValueError, 'Expected one'):
                wheel_path(root)

    def test_requirements_marker_selects_python_version(self):
        source = ROOT / 'scripts' / 'development' / 'check-python-deps.py'
        spec = importlib.util.spec_from_file_location('check_python_deps', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.sys, 'version_info', (3, 13)):
            self.assertEqual('Kivy==2.3.1', module.active_requirement('Kivy==2.3.1; python_version < "3.14"'))
            self.assertIsNone(module.active_requirement('Kivy==3.0.0.dev0; python_version >= "3.14"'))
        with patch.object(module.sys, 'version_info', (3, 14)):
            self.assertIsNone(module.active_requirement('Kivy==2.3.1; python_version < "3.14"'))
            self.assertEqual('Kivy==3.0.0.dev0',
                             module.active_requirement('Kivy==3.0.0.dev0; python_version >= "3.14"'))


if __name__ == '__main__':
    unittest.main()
