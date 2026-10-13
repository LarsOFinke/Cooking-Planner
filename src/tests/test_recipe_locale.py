import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.recipes.locale import locale_from_filename


class RecipeLocaleTest(unittest.TestCase):
    def test_suffix_selects_language(self):
        self.assertEqual("de", locale_from_filename(Path("/tmp/recipes_DE.json")))
        self.assertEqual("en", locale_from_filename(Path("recipes_en.json")))

    def test_other_filenames_are_rejected(self):
        with self.assertRaises(ValueError):
            locale_from_filename(Path("recipes.json"))


if __name__ == "__main__":
    unittest.main()
