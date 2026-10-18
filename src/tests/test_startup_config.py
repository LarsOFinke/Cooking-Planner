import sys
import tempfile
import unittest
from configparser import ConfigParser
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))

from cooking_planner.launcher import bounded_number, fullscreen_enabled, preferred_locale
from cooking_planner.ui.window import fullscreen_mode, minimum_window_size


class StartupConfigTest(unittest.TestCase):
    def test_numbers_use_defaults_for_missing_invalid_and_out_of_range_values(self):
        config = ConfigParser()
        self.assertEqual(1.0, bounded_number(config, 'ui', 'scale', 1.0, 1.0, 2.0))
        config['ui'] = {'scale': '1.5', 'window_width': '99999'}
        self.assertEqual(1.5, bounded_number(config, 'ui', 'scale', 1.0, 1.0, 2.0))
        self.assertEqual(1280, bounded_number(config, 'ui', 'window_width', 1280, 900, 3840))
        config['ui']['scale'] = 'nope'
        self.assertEqual(1.0, bounded_number(config, 'ui', 'scale', 1.0, 1.0, 2.0))

    def test_locale_uses_available_catalog_and_fullscreen_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            catalogs = Path(temp)
            (catalogs / 'recipes_de.json').write_text('{}')
            config = ConfigParser()
            config['ui'] = {'locale': 'EN', 'fullscreen': 'yes'}
            with patch('cooking_planner.launcher.catalog_directory', return_value=catalogs):
                self.assertEqual('de', preferred_locale(config))
                (catalogs / 'recipes_en.json').write_text('{}')
                self.assertEqual('en', preferred_locale(config))
            self.assertTrue(fullscreen_enabled(config))
            config['ui']['fullscreen'] = 'invalid'
            self.assertFalse(fullscreen_enabled(config))

    def test_fullscreen_uses_display_resolution_with_kivy_2(self):
        with patch('kivy.__version__', '2.3.1'):
            self.assertEqual('auto', fullscreen_mode(True))
            self.assertIs(False, fullscreen_mode(False))
        with patch('kivy.__version__', '3.0.0.dev0'):
            self.assertIs(True, fullscreen_mode(True))

    def test_window_minimum_tracks_ui_scale(self):
        self.assertEqual((900, 650), minimum_window_size(1.0))
        self.assertEqual((1440, 900), minimum_window_size(2.0))


if __name__ == '__main__':
    unittest.main()
