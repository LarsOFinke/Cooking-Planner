"""Shared catalog synchronization and image attribution storage."""

import csv
import json
from pathlib import Path

def read_catalog(root, *, allow_existing_refs=False):
    catalog_path = root / 'image_catalog.json'
    if catalog_path.exists():
        return json.loads(catalog_path.read_text('utf-8'))
    data_dir = root.parent
    de = json.loads((data_dir / 'recipes_de.json').read_text(encoding='utf-8'))
    en = json.loads((data_dir / 'recipes_en.json').read_text(encoding='utf-8'))
    german = {recipe['id']: recipe for recipe in de['recipes']}
    english = {recipe['id']: recipe for recipe in en['recipes']}
    if len(german) != 586 or set(german) != set(english):
        raise ValueError('Expected 586 shared recipe IDs across both locale files')
    if any(recipe.get('images') for recipe in de['recipes'] + en['recipes']):
        if not allow_existing_refs:
            raise ValueError('Image references exist but image_catalog.json is missing; run the image import script first')
        for recipe_id in german:
            if german[recipe_id].get('images', []) != english[recipe_id].get('images', []):
                raise ValueError(f'Locale image references differ for {recipe_id}')
    return {'metadata': {'source': 'Wikimedia Commons and locally supplied images'}, 'recipes': [
        {'recipe_id': recipe_id, 'folder': recipe_id,
         'name_de': german[recipe_id]['name'], 'name_en': english[recipe_id]['name'],
         'status': 'pending', 'images': []}
        for recipe_id in english
    ]}


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def synchronize_locales(root: Path, catalog: dict) -> None:
    """Set identical image references in both localized databases; never refer to nonexistent files."""
    recipes_by_id = {r['recipe_id']: r for r in catalog['recipes']}
    for locale in ('de', 'en'):
        target = root.parent / f'recipes_{locale}.json'
        if not target.exists():
            raise FileNotFoundError(f'Missing companion file {target}. Extract full package first.')
        db = json.loads(target.read_text(encoding='utf-8'))
        if set(x['id'] for x in db['recipes']) != set(recipes_by_id):
            raise ValueError(f'Inconsistent recipe IDs in {target}')
        for entry in db['recipes']:
            info = recipes_by_id[entry['id']]
            images = [
                'recipe_images/' + image['path']
                for image in info['images']
                if (root / image['path']).is_file()
            ]
            if images:
                entry['image_folder'] = 'recipe_images/' + entry['id']
                entry['images'] = images
            else:
                entry.pop('image_folder', None)
                entry.pop('images', None)
        available = sum(bool(x.get('images')) for x in db['recipes'])
        if available:
            db['metadata']['images_available'] = available
        else:
            db['metadata'].pop('images_available', None)
        write_json(target, db)


def write_attributions(root: Path, recipes: list[dict]):
    rows = []
    for rec in recipes:
        for img in rec['images']:
            rows.append({
                'recipe_id': rec['recipe_id'], 'image_id': img['image_id'], 'name_de': rec['name_de'],
                'name_en': rec['name_en'], 'image_path': img['path'],
                'author': img.get('author', ''), 'license': img.get('license', ''),
                'license_url': img.get('license_url', ''), 'source_url': img.get('source_url', ''),
                'file_title': img.get('file_title', ''), 'credit': img.get('credit', ''),
                'source_type': img.get('source_type', 'commons'),
                'rights_status': img.get('rights_status', 'licensed'),
                'modifications': img.get('modifications', 'Verkleinert und in JPEG umgewandelt'
                                         if img.get('source_url') else ''),
            })
    if not rows:
        return 0
    with (root / 'IMAGE_ATTRIBUTIONS.csv').open('w', encoding='utf-8-sig', newline='') as h:
        writer = csv.DictWriter(
            h, fieldnames=list(rows[0]) if rows else ['recipe_id', 'image_id', 'name_de', 'name_en',
                                                       'image_path', 'author', 'license', 'license_url',
                                                       'source_url', 'file_title', 'credit'],
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(rows)
    with (root / 'IMAGE_ATTRIBUTIONS.md').open('w', encoding='utf-8') as h:
        h.write('# Bildquellen und Lizenzhinweise\n\n')
        h.write('Bitte prüfe vor Veröffentlichung die Lizenzbedingungen jedes einzelnen Bildes.\n')
        h.write('Bildnachweise müssen auch in deiner App sichtbar sein, falls die Lizenz das verlangt.\n\n')
        for row in rows:
            h.write(f"- **{row['name_de']}** · `{row['image_path']}` — ")
            h.write((row['author'] or 'Urheber offen') + ' · ')
            h.write(row['license'] or 'Bildrechte noch nicht dokumentiert')
            if row['source_url']:
                h.write(f" · [Quelle]({row['source_url']})")
            if row['license_url']:
                h.write(f" · [Lizenz]({row['license_url']})")
            if row['modifications']:
                h.write(f" · {row['modifications']}")
            h.write('\n')
    return len(rows)
