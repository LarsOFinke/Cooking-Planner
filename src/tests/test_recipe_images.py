import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.recipes.images import attributions, image_file


class RecipeImagesTest(unittest.TestCase):
    def test_only_existing_image_for_matching_recipe_is_resolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = root / 'recipe_images' / 'some-dish' / 'image_01.jpg'
            second = root / 'recipe_images' / 'some-dish' / 'image_02.png'
            photo.parent.mkdir(parents=True)
            photo.write_bytes(b'photo')
            second.write_bytes(b'photo two')
            with patch.dict(os.environ, {'COOKING_PLANNER_CATALOG_DIR': temporary}):
                self.assertEqual(photo, image_file('some-dish', 'recipe_images/some-dish/image_01.jpg'))
                self.assertEqual(second, image_file('some-dish', 'recipe_images/some-dish/image_02.png'))
                self.assertIsNone(image_file('other-dish', 'recipe_images/some-dish/image_01.jpg'))
                self.assertIsNone(image_file('../some-dish', 'recipe_images/../some-dish/image_01.jpg'))
                self.assertIsNone(image_file('some-dish', 'recipe_images/some-dish/image_03.png'))

    def test_attributions_are_read_from_active_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'recipe_images' / 'IMAGE_ATTRIBUTIONS.csv'
            source.parent.mkdir()
            source.write_text('image_path,author,license\nsome-dish/image_01.jpg,Ada,CC BY 4.0\n')
            with patch.dict(os.environ, {'COOKING_PLANNER_CATALOG_DIR': temporary}):
                self.assertEqual('Ada', attributions()['recipe_images/some-dish/image_01.jpg']['author'])


if __name__ == '__main__':
    unittest.main()
