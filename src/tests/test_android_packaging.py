import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'frontend'))

from cooking_planner import paths  # noqa: E402
from cooking_planner.launcher import default_data_dir  # noqa: E402


class AndroidPackagingTest(unittest.TestCase):
    def test_android_catalogs_resolve_beside_staged_entry_point(self):
        with patch.dict(os.environ, {'ANDROID_ARGUMENT': '/data/user/0/org.cookingplanner'}), \
             patch.object(paths, '__file__', '/tmp/apk/source/cooking_planner/paths.py'):
            self.assertEqual(Path('/tmp/apk/source/catalogs'), paths.catalog_directory())

    def test_android_writable_data_uses_app_private_storage(self):
        android = types.ModuleType('android')
        storage = types.ModuleType('android.storage')
        storage.app_storage_path = lambda: '/data/user/0/org.cookingplanner/files'
        with patch.dict(os.environ, {'ANDROID_ARGUMENT': '/data/user/0/org.cookingplanner'}), \
             patch.dict(sys.modules, {'android': android, 'android.storage': storage}):
            self.assertEqual(Path('/data/user/0/org.cookingplanner/files/cooking-planner'), default_data_dir())

    def test_stage_contains_entry_point_packages_catalogs_and_images(self):
        spec = importlib.util.spec_from_file_location('android_stage', ROOT / 'scripts/build/android/stage.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'project'
            for folder in ('src/frontend/cooking_planner', 'src/backend/cooking_planner_backend',
                           'data/recipe_images/sample'):
                (root / folder).mkdir(parents=True)
            (root / 'src/frontend/main.py').write_text('pass\n')
            (root / 'src/frontend/cooking_planner/__init__.py').write_text('')
            (root / 'src/backend/cooking_planner_backend/__init__.py').write_text('')
            (root / 'data/recipes_en.json').write_text('{}')
            (root / 'data/recipe_images/sample/image_01.jpg').write_bytes(b'image')
            (root / 'pyproject.toml').write_text('[project]\nversion = "1.2.3"\n')
            (root / 'scripts/build/android').mkdir(parents=True)
            (root / 'scripts/build/android/buildozer.spec').write_text('[app]\nversion = 0.0.0\n')
            destination = Path(temp) / 'staged'
            self.assertEqual(destination, module.stage(root, destination))
            self.assertIn('version = 1.2.3', (destination.parent / 'buildozer.spec').read_text())
            self.assertTrue((destination / 'main.py').is_file())
            self.assertTrue((destination / 'cooking_planner/__init__.py').is_file())
            self.assertTrue((destination / 'cooking_planner_backend/__init__.py').is_file())
            self.assertTrue((destination / 'catalogs/recipes_en.json').is_file())
            self.assertTrue((destination / 'catalogs/recipe_images/sample/image_01.jpg').is_file())

    def test_apk_check_requires_no_permissions_and_disables_backup(self):
        spec = importlib.util.spec_from_file_location('android_verify', ROOT / 'scripts/build/android/verify-package.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = 'A: android:allowBackup(0x01010280)=(type 0x12)0x0\n'
        with patch.object(module, 'find_aapt', return_value='aapt'), \
             patch.object(module.subprocess, 'check_output', side_effect=['package: name=app\n', manifest]):
            module.verify(Path('/tmp/example.apk'))
        with patch.object(module, 'find_aapt', return_value='aapt'), \
             patch.object(module.subprocess, 'check_output', side_effect=[
                 "uses-permission: name='android.permission.INTERNET'\n", manifest]):
            with self.assertRaisesRegex(RuntimeError, 'Unexpected Android permissions'):
                module.verify(Path('/tmp/example.apk'))


if __name__ == '__main__':
    unittest.main()
