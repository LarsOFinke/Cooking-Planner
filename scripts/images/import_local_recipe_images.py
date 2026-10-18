#!/usr/bin/env python3
"""Index user-supplied recipe pictures by stable ID without changing their files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from image_file import PHOTO_NAME, check_photo
from recipe_image_catalog import (
    attribution_documents,
    commit_documents,
    json_bytes,
    locale_documents,
    read_catalog,
    recover_documents,
)

ROOT = Path(__file__).resolve().parents[2] / 'data' / 'recipe_images'
CREDIT_FIELDS = ('author', 'license', 'source_url', 'license_url', 'credit')


def scan(root: Path, ids: set[str]) -> dict[str, list[tuple[Path, str]]]:
    found = {}
    if not root.exists():
        return found
    for folder in root.iterdir():
        if not folder.is_dir():
            if folder.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                raise ValueError(f'Bild ohne Rezept-ID-Ordner: {folder}')
            continue
        if folder.name not in ids:
            raise ValueError(f'Unbekannte Rezept-ID als Bildordner: {folder.name}')
        numbered = {}
        for path in folder.iterdir():
            match = PHOTO_NAME.fullmatch(path.name) if path.is_file() else None
            if match is None:
                raise ValueError(f'Nicht unterstützte Datei in Rezeptordner: {path}')
            number = int(match.group(1))
            if number in numbered:
                raise ValueError(f'Doppelte Bildnummer in {folder}')
            numbered[number] = (path, check_photo(path))
        if numbered:
            if sorted(numbered) != list(range(1, len(numbered) + 1)) or len(numbered) > 3:
                raise ValueError(f'{folder}: 1–3 fortlaufende Bildnummern ab image_01 erforderlich')
            found[folder.name] = [numbered[index] for index in sorted(numbered)]
        else:
            raise ValueError(f'Leerer Bildordner: {folder}')
    return found


def load_credits(path: Path) -> dict:
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding='utf-8'))
    if document.get('version') != 1 or not isinstance(document.get('images'), dict):
        raise ValueError(f'Ungültige lokale Bildnachweise: {path}')
    return document['images']


def import_images(root: Path) -> tuple[int, int]:
    recover_documents(root.parent)
    catalog = read_catalog(root, allow_existing_refs=True)
    by_id = {entry['recipe_id']: entry for entry in catalog['recipes']}
    found = scan(root, set(by_id))
    credits_path = root / 'LOCAL_IMAGE_CREDITS.json'
    credits = load_credits(credits_path)
    updated_credits = {}
    used_hashes = set()
    local_count = 0
    for recipe_id, entry in by_id.items():
        old = {image['path']: image for image in entry['images']}
        updated = []
        for path, digest in found.get(recipe_id, []):
            relative = f'{recipe_id}/{path.name}'
            previous = old.get(relative, {})
            if digest in used_hashes:
                raise ValueError(f'Doppeltes Bild gefunden: {path}')
            used_hashes.add(digest)
            if previous.get('source_type', 'local') == 'commons':
                if previous.get('sha256') != digest:
                    raise ValueError(f'Commons-Bild wurde verändert: {path}')
                updated.append(previous)
                continue
            record = credits.get(relative, {})
            if record.get('sha256') != digest:
                record = {'author': '', 'license': '', 'source_url': '', 'license_url': '',
                          'credit': '', 'rights_status': 'pending'}
            status = record.get('rights_status', 'pending')
            if status not in ('pending', 'approved', 'licensed'):
                raise ValueError(f'Ungültiger Rechte-Status für {relative}')
            if status != 'pending' and (not record.get('author') or not record.get('license')):
                raise ValueError(f'Urheber und Lizenz fehlen für {relative}')
            if status == 'licensed' and not record.get('source_url'):
                raise ValueError(f'Quellen-URL fehlt für lizenziertes Bild {relative}')
            record = {field: record.get(field, '') for field in CREDIT_FIELDS} | {
                'rights_status': status, 'sha256': digest,
            }
            updated_credits[relative] = record
            updated.append({'image_id': f'{recipe_id}-{len(updated) + 1:02d}',
                            'path': relative, 'file_title': path.name,
                            'source_type': 'local', 'rights_status': status,
                            'bytes': path.stat().st_size, 'sha256': digest,
                            **{field: record[field] for field in CREDIT_FIELDS}})
            local_count += 1
        # A deleted Commons image must be restored, not silently forgotten.
        missing_commons = [path for path, info in old.items()
                           if info.get('source_type') == 'commons' and path not in {item['path'] for item in updated}]
        if missing_commons:
            raise ValueError(f'Fehlendes Commons-Bild: {missing_commons[0]}')
        entry['images'] = updated
        if updated:
            entry['status'] = 'downloaded'
    documents = locale_documents(root, catalog)
    if any(entry['images'] for entry in catalog['recipes']):
        documents[root / 'LOCAL_IMAGE_CREDITS.json'] = json_bytes({'version': 1, 'images': updated_credits})
        documents[root / 'image_catalog.json'] = json_bytes(catalog)
    documents.update(attribution_documents(root, catalog['recipes']))
    commit_documents(root.parent, documents)
    return len(found), local_count


def main() -> int:
    parser = argparse.ArgumentParser(description='Vorhandene Rezeptbilder per ID in beide Sprachkataloge übernehmen')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    recipes, images = import_images(args.root)
    print(f'{images} lokale Bilder für {recipes} Rezepte eingebunden. Bildrechte: '
          f'{args.root / "LOCAL_IMAGE_CREDITS.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
