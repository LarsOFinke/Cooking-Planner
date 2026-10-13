"""Check local image ingestion across both real recipe locales."""

import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'images'))

from import_local_recipe_images import import_images  # noqa: E402
import verify_recipe_images  # noqa: E402


def png(seed):
    width = height = 48
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            pixels.extend(((x * 7 + seed) % 256, (y * 11 + seed) % 256, (x * y + seed) % 256))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(pixels))) + chunk(b'IEND', b''))


class ImageImportTest(unittest.TestCase):
    def test_two_images_sync_both_locales_and_reject_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            for locale in ('de', 'en'):
                document = json.loads((ROOT / 'data' / f'recipes_{locale}.json').read_text(encoding='utf-8'))
                for recipe in document['recipes']:
                    recipe.pop('images', None)
                    recipe.pop('image_folder', None)
                document['metadata'].pop('images_available', None)
                (data / f'recipes_{locale}.json').write_text(json.dumps(document), encoding='utf-8')
            folder = data / 'recipe_images' / 'dz-algerischer-couscous'
            folder.mkdir(parents=True)
            (folder / 'image_01.png').write_bytes(png(5))
            (folder / 'image_02.png').write_bytes(png(19))
            (folder / 'image_03.png').write_bytes(png(31))
            self.assertEqual((1, 3), import_images(data / 'recipe_images'))
            self.assertEqual((1, 3), import_images(data / 'recipe_images'))
            refs = []
            for locale in ('de', 'en'):
                document = json.loads((data / f'recipes_{locale}.json').read_text(encoding='utf-8'))
                refs.append(next(recipe['images'] for recipe in document['recipes']
                                 if recipe['id'] == 'dz-algerischer-couscous'))
            self.assertEqual(refs[0], refs[1])
            self.assertEqual(3, len(refs[0]))
            with patch.object(verify_recipe_images, 'DATA', data), \
                 patch.object(verify_recipe_images, 'IMAGES', data / 'recipe_images'):
                self.assertEqual(0, verify_recipe_images.main())
            duplicate = data / 'recipe_images' / 'dz-makroud'
            duplicate.mkdir()
            (duplicate / 'image_01.png').write_bytes((folder / 'image_01.png').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Doppeltes Bild'):
                import_images(data / 'recipe_images')


if __name__ == '__main__':
    unittest.main()
