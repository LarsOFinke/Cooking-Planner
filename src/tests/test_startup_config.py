import sys
import tempfile
import unittest
from configparser import ConfigParser
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))

from cooking_planner.launcher import bounded_number, fullscreen_enabled, preferred_locale


class StartupConfigTest(unittest.TestCase):
    def test_numbers_use_defaults_for_missing_invalid_and_out_of_range_values(self):
        config = ConfigParser()
        self.assertEqual(10.0, bounded_number(config, 'backend', 'request_timeout', 10.0, 1.0, 120.0))
        config['backend'] = {'request_timeout': '30.5', 'port': '99999'}
        self.assertEqual(30.5, bounded_number(config, 'backend', 'request_timeout', 10.0, 1.0, 120.0))
        self.assertEqual(8765, bounded_number(config, 'backend', 'port', 8765, 1, 65535))
        config['backend']['request_timeout'] = 'nope'
        self.assertEqual(10.0, bounded_number(config, 'backend', 'request_timeout', 10.0, 1.0, 120.0))

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


if __name__ == '__main__':
    unittest.main()
