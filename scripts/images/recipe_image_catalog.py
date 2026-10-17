"""Shared catalog synchronization and image attribution storage."""

import csv
import io
import json
import os
from pathlib import Path
from shutil import copy2, rmtree


def locale_recipes(data_dir: Path) -> tuple[dict, dict]:
    documents = [json.loads((data_dir / f'recipes_{locale}.json').read_text(encoding='utf-8'))
                 for locale in ('de', 'en')]
    ids = [[recipe['id'] for recipe in document['recipes']] for document in documents]
    if any(not values or len(values) != len(set(values)) for values in ids) or set(ids[0]) != set(ids[1]):
        raise ValueError('Localized catalogs must have the same unique recipe IDs')
    return documents[0], documents[1]


def read_catalog(root, *, allow_existing_refs=False):
    de, en = locale_recipes(root.parent)
    german = {recipe['id']: recipe for recipe in de['recipes']}
    english = {recipe['id']: recipe for recipe in en['recipes']}
    catalog_path = root / 'image_catalog.json'
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text('utf-8'))
        entries = catalog['recipes']
        ids = [entry['recipe_id'] for entry in entries]
        if len(ids) != len(set(ids)) or set(ids) - set(english):
            raise ValueError('Image catalog has duplicate or unknown recipe IDs')
        for entry in entries:
            recipe_id = entry['recipe_id']
            entry['name_de'] = german[recipe_id]['name']
            entry['name_en'] = english[recipe_id]['name']
        for recipe_id in english:
            if recipe_id not in ids:
                entries.append(new_entry(recipe_id, german, english))
        return catalog
    if any(recipe.get('images') for recipe in de['recipes'] + en['recipes']):
        if not allow_existing_refs:
            raise ValueError('Image references exist but image_catalog.json is missing; run the image import script first')
        for recipe_id in german:
            if german[recipe_id].get('images', []) != english[recipe_id].get('images', []):
                raise ValueError(f'Locale image references differ for {recipe_id}')
    return {'metadata': {'source': 'Wikimedia Commons and locally supplied images'},
            'recipes': [new_entry(recipe_id, german, english) for recipe_id in english]}


def new_entry(recipe_id: str, german: dict, english: dict) -> dict:
    return {'recipe_id': recipe_id, 'folder': recipe_id,
            'name_de': german[recipe_id]['name'], 'name_en': english[recipe_id]['name'],
            'status': 'pending', 'images': []}


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def locale_documents(root: Path, catalog: dict) -> dict[Path, bytes]:
    """Prepare matching locale references before writing either catalog."""
    recipes_by_id = {r['recipe_id']: r for r in catalog['recipes']}
    if len(recipes_by_id) != len(catalog['recipes']):
        raise ValueError('Duplicate recipe IDs in image catalog')
    documents = {}
    for locale in ('de', 'en'):
        target = root.parent / f'recipes_{locale}.json'
        if not target.exists():
            raise FileNotFoundError(f'Missing companion file {target}. Extract full package first.')
        db = json.loads(target.read_text(encoding='utf-8'))
        ids = [entry['id'] for entry in db['recipes']]
        if len(ids) != len(set(ids)) or set(ids) != set(recipes_by_id):
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
        documents[target] = json_bytes(db)
    return documents


def attribution_documents(root: Path, recipes: list[dict]) -> dict[Path, bytes | None]:
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
        return {root / 'IMAGE_ATTRIBUTIONS.csv': None, root / 'IMAGE_ATTRIBUTIONS.md': None}
    csv_output = io.StringIO(newline='')
    writer = csv.DictWriter(csv_output, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    markdown_output = io.StringIO()
    markdown_output.write('# Bildquellen und Lizenzhinweise\n\n')
    markdown_output.write('Bitte prüfe vor Veröffentlichung die Lizenzbedingungen jedes einzelnen Bildes.\n')
    markdown_output.write('Bildnachweise müssen auch in deiner App sichtbar sein, falls die Lizenz das verlangt.\n\n')
    for row in rows:
        markdown_output.write(f"- **{row['name_de']}** · `{row['image_path']}` — ")
        markdown_output.write((row['author'] or 'Urheber offen') + ' · ')
        markdown_output.write(row['license'] or 'Bildrechte noch nicht dokumentiert')
        if row['source_url']:
            markdown_output.write(f" · [Quelle]({row['source_url']})")
        if row['license_url']:
            markdown_output.write(f" · [Lizenz]({row['license_url']})")
        if row['modifications']:
            markdown_output.write(f" · {row['modifications']}")
        markdown_output.write('\n')
    return {root / 'IMAGE_ATTRIBUTIONS.csv': csv_output.getvalue().encode('utf-8-sig'),
            root / 'IMAGE_ATTRIBUTIONS.md': markdown_output.getvalue().encode('utf-8')}


def recover_documents(data_dir: Path) -> None:
    recovery = data_dir / '.image-import-recovery'
    if not recovery.exists():
        return
    manifest = recovery / 'manifest.json'
    if manifest.exists():
        for index, relative in enumerate(json.loads(manifest.read_text(encoding='utf-8'))):
            target = data_dir / relative
            backup = recovery / f'{index}.old'
            if backup.exists():
                temporary = recovery / f'{index}.restore'
                copy2(backup, temporary)
                os.replace(temporary, target)
            else:
                target.unlink(missing_ok=True)
    rmtree(recovery)


def commit_documents(data_dir: Path, documents: dict[Path, bytes | None]) -> None:
    """Keep backups until every related file has been replaced successfully."""
    recovery = data_dir / '.image-import-recovery'
    recovery.mkdir()
    try:
        paths = list(documents)
        for index, target in enumerate(paths):
            if target.exists():
                copy2(target, recovery / f'{index}.old')
            if documents[target] is not None:
                (recovery / f'{index}.new').write_bytes(documents[target])
        (recovery / 'manifest.tmp').write_text(
            json.dumps([str(path.relative_to(data_dir)) for path in paths]), encoding='utf-8')
        os.replace(recovery / 'manifest.tmp', recovery / 'manifest.json')
        for index, target in enumerate(paths):
            if documents[target] is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(recovery / f'{index}.new', target)
    except Exception:
        recover_documents(data_dir)
        raise
    else:
        rmtree(recovery)
