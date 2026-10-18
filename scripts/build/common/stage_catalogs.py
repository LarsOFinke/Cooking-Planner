"""Prepare compact, read-only recipe catalogs for desktop distributions."""

import csv
import json
from pathlib import Path
from shutil import rmtree

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
MAX_IMAGE_SIZE = 960
JPEG_QUALITY = 74


def stage_catalogs(source: Path, destination: Path) -> tuple[int, int]:
    documents = {}
    references = {}
    for locale in ('de', 'en'):
        document = json.loads((source / f'recipes_{locale}.json').read_text(encoding='utf-8'))
        documents[locale] = document
        for recipe in document['recipes']:
            images = recipe.get('images', [])
            previous = references.setdefault(recipe['id'], images)
            if previous != images:
                raise ValueError(f"Image references differ between locales for {recipe['id']}")

    converted = {}
    total_source = 0
    total_staged = 0
    for recipe_id, images in references.items():
        for reference in images:
            original = source / reference
            if not original.is_file() or original.parent.name != recipe_id:
                raise ValueError(f'Invalid or missing recipe image: {reference}')
            target_reference = str(Path(reference).with_suffix('.jpg')).replace('\\', '/')
            target = destination / target_reference
            if target_reference in converted.values():
                raise ValueError(f'Duplicate staged image: {target_reference}')
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(original) as photo:
                photo.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
                if photo.mode != 'RGB':
                    photo = photo.convert('RGB')
                photo.save(target, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
            converted[reference] = target_reference
            total_source += original.stat().st_size
            total_staged += target.stat().st_size

    for locale, document in documents.items():
        for recipe in document['recipes']:
            if 'images' in recipe:
                recipe['images'] = [converted[reference] for reference in recipe['images']]
        (destination / f'recipes_{locale}.json').write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    source_images = source / 'recipe_images'
    destination_images = destination / 'recipe_images'
    with (source_images / 'IMAGE_ATTRIBUTIONS.csv').open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)
    if fields is None or {f'recipe_images/{row["image_path"]}' for row in rows} != set(converted):
        raise ValueError('Image attributions do not match recipe references')
    for row in rows:
        row['image_path'] = converted[f'recipe_images/{row["image_path"]}'].removeprefix('recipe_images/')
    with (destination_images / 'IMAGE_ATTRIBUTIONS.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    markdown = (source_images / 'IMAGE_ATTRIBUTIONS.md').read_text(encoding='utf-8')
    for old, new in converted.items():
        markdown = markdown.replace(f'`{old.removeprefix("recipe_images/")}`',
                                    f'`{new.removeprefix("recipe_images/")}`')
    (destination_images / 'IMAGE_ATTRIBUTIONS.md').write_text(markdown, encoding='utf-8')
    return total_source, total_staged


if __name__ == '__main__':
    target = ROOT / 'build' / 'catalogs'
    if target.exists():
        rmtree(target)
    target.mkdir(parents=True)
    try:
        original_size, package_size = stage_catalogs(ROOT / 'data', target)
    except Exception:
        rmtree(target)
        raise
    print(f'Staged {original_size // 1024 // 1024} MiB of photos as '
          f'{package_size // 1024 // 1024} MiB of JPEGs in {target}')
