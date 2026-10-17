"""Check local image ingestion across both real recipe locales."""

import json
import os
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
    def test_new_recipe_ids_extend_existing_image_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            images = data / 'recipe_images'
            folder = images / 'xx-one'
            folder.mkdir(parents=True)
            (folder / 'image_01.png').write_bytes(png(5))
            for locale in ('de', 'en'):
                document = {'metadata': {}, 'recipes': [{'id': 'xx-one', 'name': f'One {locale}'}]}
                (data / f'recipes_{locale}.json').write_text(json.dumps(document))
            self.assertEqual((1, 1), import_images(images))
            for locale in ('de', 'en'):
                path = data / f'recipes_{locale}.json'
                document = json.loads(path.read_text())
                document['recipes'].append({'id': 'yy-two', 'name': f'Two {locale}'})
                path.write_text(json.dumps(document))
            self.assertEqual((1, 1), import_images(images))
            catalog = json.loads((images / 'image_catalog.json').read_text())
            self.assertEqual(['xx-one', 'yy-two'], [entry['recipe_id'] for entry in catalog['recipes']])
            with patch.object(verify_recipe_images, 'DATA', data), \
                 patch.object(verify_recipe_images, 'IMAGES', images):
                self.assertEqual(0, verify_recipe_images.main())

    def test_failed_locale_write_restores_every_related_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            for locale in ('de', 'en'):
                source = ROOT / 'data' / f'recipes_{locale}.json'
                (data / source.name).write_bytes(source.read_bytes())
            folder = data / 'recipe_images' / 'dz-algerischer-couscous'
            folder.mkdir(parents=True)
            (folder / 'image_01.png').write_bytes(png(5))
            before = {path: path.read_bytes() for path in data.glob('recipes_*.json')}
            replace = os.replace
            failed = False

            def fail_once(source, target):
                nonlocal failed
                if not failed and str(target).endswith('recipes_en.json'):
                    failed = True
                    raise OSError('simulated write failure')
                return replace(source, target)

            with patch('recipe_image_catalog.os.replace', side_effect=fail_once):
                with self.assertRaisesRegex(OSError, 'simulated write failure'):
                    import_images(data / 'recipe_images')
            self.assertTrue(failed)
            self.assertEqual(before, {path: path.read_bytes() for path in data.glob('recipes_*.json')})
            self.assertFalse((data / 'recipe_images/image_catalog.json').exists())
            self.assertFalse((data / '.image-import-recovery').exists())

    def test_interrupted_import_recovers_before_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            for locale in ('de', 'en'):
                source = ROOT / 'data' / f'recipes_{locale}.json'
                (data / source.name).write_bytes(source.read_bytes())
            folder = data / 'recipe_images' / 'dz-algerischer-couscous'
            folder.mkdir(parents=True)
            (folder / 'image_01.png').write_bytes(png(5))
            replace = os.replace

            def interrupt(source, target):
                if str(target).endswith('recipes_en.json'):
                    raise KeyboardInterrupt('simulated process interruption')
                return replace(source, target)

            with patch('recipe_image_catalog.os.replace', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    import_images(data / 'recipe_images')
            self.assertTrue((data / '.image-import-recovery/manifest.json').exists())
            with patch.object(verify_recipe_images, 'DATA', data), \
                 patch.object(verify_recipe_images, 'IMAGES', data / 'recipe_images'):
                with self.assertRaisesRegex(ValueError, 'Interrupted image import'):
                    verify_recipe_images.main()
            self.assertEqual((1, 1), import_images(data / 'recipe_images'))
            self.assertFalse((data / '.image-import-recovery').exists())

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
