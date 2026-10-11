"""Validate both locale references, real picture files and rights records."""

import csv
import hashlib
import json
import re
import struct
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / 'data'
IMAGES = DATA / 'recipe_images'
PHOTO_NAME = re.compile(r'image_([0-9]{2})\.(jpg|jpeg|png|webp)')


def load(locale):
    document = json.loads((DATA / f'recipes_{locale}.json').read_text(encoding='utf-8'))
    recipes = document['recipes']
    ids = [recipe['id'] for recipe in recipes]
    if len(ids) != 586 or len(set(ids)) != 586:
        raise ValueError(f'{locale}: expected 586 unique recipe IDs')
    return document, {recipe['id']: recipe for recipe in recipes}


def check_photo(target: Path) -> str:
    data = target.read_bytes()
    if len(data) < 1024:
        raise ValueError(f'Empty or tiny image: {target}')
    if target.suffix in ('.jpg', '.jpeg'):
        valid = data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9')
    elif target.suffix == '.png':
        valid = data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-32:]
    else:
        valid = (data.startswith(b'RIFF') and data[8:12] == b'WEBP'
                 and struct.unpack('<I', data[4:8])[0] + 8 == len(data))
    if not valid:
        raise ValueError(f'Invalid image content: {target}')
    return hashlib.sha256(data).hexdigest()


def main():
    de_doc, german = load('de')
    en_doc, english = load('en')
    if set(german) != set(english):
        raise ValueError('Locale files do not share the same recipe IDs')
    referenced = {}
    hashes = set()
    covered = 0
    for recipe_id in english:
        de = german[recipe_id]
        en = english[recipe_id]
        images = en.get('images', [])
        if images != de.get('images', []):
            raise ValueError(f'{recipe_id}: locale image references differ')
        if not images:
            if de.get('image_folder') or en.get('image_folder') or 'images' in de or 'images' in en:
                raise ValueError(f'{recipe_id}: empty image placeholder')
            continue
        covered += 1
        if not 1 <= len(images) <= 3 or len(images) != len(set(images)):
            raise ValueError(f'{recipe_id}: expected 1–3 distinct photos')
        expected_folder = f'recipe_images/{recipe_id}'
        if de.get('image_folder') != expected_folder or en.get('image_folder') != expected_folder:
            raise ValueError(f'{recipe_id}: image folder does not match ID')
        for index, reference in enumerate(images, 1):
            relative = Path(reference)
            match = PHOTO_NAME.fullmatch(relative.name)
            if not match or int(match.group(1)) != index or relative.parent.as_posix() != expected_folder:
                raise ValueError(f'{recipe_id}: invalid path {reference}')
            target = DATA / relative
            if not target.is_file():
                raise ValueError(f'{recipe_id}: missing image {reference}')
            digest = check_photo(target)
            if digest in hashes:
                raise ValueError(f'{recipe_id}: duplicate image content')
            hashes.add(digest)
            referenced[reference] = digest
    for document in (de_doc, en_doc):
        if document['metadata'].get('images_available', 0) != covered:
            raise ValueError('images_available metadata does not match actual image coverage')
    actual = {path.relative_to(DATA).as_posix() for path in IMAGES.glob('*/*') if path.is_file()} if IMAGES.exists() else set()
    if actual != set(referenced):
        raise ValueError(f'Photo file/reference mismatch: {len(actual - referenced.keys())} orphaned, '
                         f'{len(referenced.keys() - actual)} missing')
    if referenced:
        catalog_path = IMAGES / 'image_catalog.json'
        attribution_path = IMAGES / 'IMAGE_ATTRIBUTIONS.csv'
        if not catalog_path.is_file() or not attribution_path.is_file():
            raise ValueError('Image catalog or attribution table is missing')
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
        entries = {'recipe_images/' + image['path']: image
                   for recipe in catalog['recipes'] for image in recipe['images']}
        if set(entries) != set(referenced):
            raise ValueError('Image catalog and locale references differ')
        with attribution_path.open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file))
        credits = {'recipe_images/' + row['image_path']: row for row in rows}
        if set(credits) != set(referenced) or len(rows) != len(referenced):
            raise ValueError('Image attributions do not match files')
        local = {}
        pending = 0
        for reference, digest in referenced.items():
            entry = entries[reference]
            row = credits[reference]
            if entry.get('sha256') != digest or row.get('recipe_id') != reference.split('/')[1]:
                raise ValueError(f'Catalog hash or attribution ID mismatch: {reference}')
            status = row.get('rights_status')
            if status == 'pending':
                pending += 1
            elif status in ('approved', 'licensed'):
                if not row.get('author') or not row.get('license'):
                    raise ValueError(f'Incomplete rights for {reference}')
                if status == 'licensed' and not row.get('source_url'):
                    raise ValueError(f'Missing source URL for {reference}')
            else:
                raise ValueError(f'Invalid rights status for {reference}')
            if row.get('source_type') == 'local':
                local[reference.removeprefix('recipe_images/')] = digest
        local_path = IMAGES / 'LOCAL_IMAGE_CREDITS.json'
        if local:
            document = json.loads(local_path.read_text(encoding='utf-8'))
            if set(document['images']) != set(local):
                raise ValueError('Local image credits do not match local pictures')
            for reference, digest in local.items():
                if document['images'][reference].get('sha256') != digest:
                    raise ValueError(f'Local image credit hash mismatch: {reference}')
    else:
        pending = 0
        if (IMAGES / 'IMAGE_ATTRIBUTIONS.csv').exists():
            raise ValueError('Empty attribution placeholder exists')
    empty_dirs = [path for path in IMAGES.iterdir() if path.is_dir() and not any(path.iterdir())] if IMAGES.exists() else []
    if empty_dirs:
        raise ValueError(f'{len(empty_dirs)} empty image directories remain')
    print(f'{covered}/586 Rezepte mit Bildern; {len(referenced)} unterschiedliche Bilddateien; '
          f'{pending} Bildrechte offen.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
