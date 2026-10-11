#!/usr/bin/env python3
"""Download Commons-licensed example food photographs for Cooking-Planner recipes.

Run from an internet-connected computer. This program NEVER invents image paths,
checks the declared license, and writes credits alongside all downloaded photos.
"""
from __future__ import annotations

import argparse
import html
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

from recipe_image_catalog import read_catalog, synchronize_locales, write_attributions, write_json

try:
    import requests
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    sys.exit('Abhängigkeiten fehlen. Bitte zuerst ausführen: python3 -m pip install -r scripts/images/requirements-images.txt')

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'CookingPlannerRecipeImageCollector/1.1 (local recipe photo catalog; Wikimedia Commons attribution retained) python-requests'
SEARCH_STOPWORDS = {'and','with','the','from','style','mit','und','der','die','das','nach','art','sauce','suppe','soup','dish','recipe','food','of','a','an','in','auf','al','alla','del','de','di','au','aus','estilo','beef','chicken'}
BAD_WORDS = {'logo','flag','map','recipe card','packaging','menu','advert','diagram','drawing','illustration','icon','signage','ingredient list','cartoon','poster','book cover','cooking class','stock photo'}
SUPPORTED_LICENSES = re.compile(r'(?:\bcc[\s-]?0\b|\bcc[\s-]+by(?:[\s-]+sa)?\b|\bpublic\s*domain\b|\bpublicdomain\b|\bpd(?:[- ]|$)|\bpdm\b)', re.I)


def clean_html(value: str | None) -> str:
    s = re.sub(r'<[^>]*?>', ' ', value or '')
    return ' '.join(html.unescape(s).split())[:400]


def normalized(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    return ' '.join(value.split())


def tokens(value: str) -> set[str]:
    return {x for x in normalized(value).split() if len(x) >= 3 and x not in SEARCH_STOPWORDS}


def term_variants(name: str) -> list[str]:
    # Parenthesized translations are useful alternate search phrases.
    variants = [name]
    simpler = re.sub(r'\([^)]*\)', '', name).strip(' -')
    parenthesized = re.findall(r'\((.*?)\)', name)
    if simpler and simpler != name:
        variants.append(simpler)
    variants.extend(s for s in parenthesized if len(s.split()) >= 2)
    return list(dict.fromkeys(x.strip() for x in variants if len(x.strip()) > 2))


def match_score(title: str, english_name: str, german_name: str, description: str = '') -> float:
    title_str = normalized(title.rsplit('.', 1)[0].replace('File:', '').replace('_', ' '))
    if any(bad in title_str for bad in BAD_WORDS):
        return -1
    best = 0.0
    for name in term_variants(english_name) + term_variants(german_name):
        candidate = normalized(name)
        if len(candidate) < 4:
            continue
        key = tokens(candidate)
        title_tokens = tokens(title_str)
        if candidate in title_str:
            score = 110 if title_str.startswith(candidate) else 103
        elif key and (key <= title_tokens):
            score = 83 + min(len(key), 4) * 3
        else:
            coverage = len(key & title_tokens) / len(key) if key else 0
            score = 20 + 60 * coverage + 15 * SequenceMatcher(None, candidate, title_str).ratio()
        if key and key.isdisjoint(title_tokens):
            score = min(score, 20)
        if description and candidate in normalized(description):
            score += 5
        best = max(best, score)
    return round(best, 2)


def license_ok(metadata: dict) -> bool:
    short = clean_html(metadata.get('LicenseShortName', {}).get('value'))
    lic = clean_html(metadata.get('License', {}).get('value'))
    url = clean_html(metadata.get('LicenseUrl', {}).get('value'))
    license_text = (short + ' ' + lic + ' ' + url).casefold()
    if re.search(r'(?<![a-z])(?:nc|nd)(?![a-z])|noncommercial|no.?derivatives', license_text):
        return False
    if any(s in (short + ' ' + lic).lower() for s in ['copyrighted', 'all rights reserved', 'unknown', 'unfree']):
        return False
    return bool(SUPPORTED_LICENSES.search(short + ' ' + lic + ' ' + url))


def image_details(page: dict) -> dict | None:
    title = page.get('title', '')
    infos = page.get('imageinfo') or []
    if not infos:
        return None
    i = infos[0]
    if not i.get('url') or (i.get('mime') or '').lower() not in ('image/jpeg','image/png','image/webp','image/tiff'):
        return None
    if min(i.get('width', 0), i.get('height', 0)) < 300:
        return None
    meta = i.get('extmetadata') or {}
    if not license_ok(meta):
        return None
    description = clean_html(meta.get('ImageDescription', {}).get('value'))
    source_url = i.get('descriptionurl', '') or 'https://commons.wikimedia.org/wiki/' + quote(title.replace(' ', '_'))
    return {
        'file_title': title,
        'description': description,
        'download_url': i.get('thumburl') or i['url'],
        'source_url': source_url,
        'author': clean_html(meta.get('Artist', {}).get('value')) or 'See source page',
        'credit': clean_html(meta.get('Credit', {}).get('value')),
        'license': clean_html(meta.get('LicenseShortName', {}).get('value')) or clean_html(meta.get('License', {}).get('value')),
        'license_url': clean_html(meta.get('LicenseUrl', {}).get('value')),
        'original_width': i['width'],
        'original_height': i['height'],
    }


def retrieve_commons(session: requests.Session, query: str, size: int = 960, limit: int = 18) -> list[dict]:
    params = {
        'action': 'query', 'format': 'json', 'formatversion': '2',
        'generator': 'search', 'gsrsearch': query,
        'gsrnamespace': 6, 'gsrlimit': limit,
        'prop': 'imageinfo', 'iiprop': 'url|mime|size|extmetadata',
        'iiurlwidth': size,
    }
    response = session.get(API, params=params, timeout=35)
    response.raise_for_status()
    data = response.json()
    if data.get('error'):
        raise RuntimeError(f'Commons API error: {data["error"]}')
    return [f for page in data.get('query', {}).get('pages', []) if (f := image_details(page))]


def make_queries(recipe: dict) -> list[str]:
    names = term_variants(recipe['name_en']) + term_variants(recipe['name_de'])
    queries = []
    for name in names:
        queries.extend([f'intitle:"{name}"', f'"{name}"'])
    return list(dict.fromkeys(queries))[:7]


def wait_after_error(attempt: int, response_status: int | None):
    if response_status == 429:
        time.sleep(min(40, 4 * (attempt + 1)))
    else:
        time.sleep(min(16, 2 ** attempt))


def get_with_retries(session, url, *, params=None, max_attempts=4, timeout=50):
    for a in range(max_attempts):
        try:
            r = session.get(url, params=params, timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                wait_after_error(a, r.status_code)
                continue
            r.raise_for_status()
            return r
        except (requests.RequestException, ConnectionError):
            if a == max_attempts - 1:
                raise
            wait_after_error(a, None)
    raise RuntimeError(f'Failed {max_attempts} times: {url}')


def search(session, query, width):
    params = {
        'action': 'query', 'format': 'json', 'formatversion': '2',
        'generator': 'search', 'gsrsearch': query,
        'gsrnamespace': 6, 'gsrlimit': 16,
        'prop': 'imageinfo', 'iiprop': 'url|mime|size|extmetadata', 'iiurlwidth': width,
    }
    r = get_with_retries(session, API, params=params)
    data = r.json()
    if data.get('error'):
        raise RuntimeError(data['error'])
    return [item for page in data.get('query', {}).get('pages', []) if (item := image_details(page))]


def save_photo(session, source, target: Path, max_side=960):
    r = get_with_retries(session, source['download_url'])
    if len(r.content) > 12_000_000:
        raise ValueError('Remote photo exceeds 12 MB')
    with Image.open(io.BytesIO(r.content)) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGB')
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        if min(image.size) < 240:
            raise ValueError('Thumbnail too small for recipe image')
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, 'JPEG', quality=83, optimize=True, progressive=True)
        return {'width': image.width, 'height': image.height, 'bytes': target.stat().st_size,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def main(argv=None):
    p = argparse.ArgumentParser(description='Bildsuche und lizenzbewusster Download für 586 Rezepte')
    p.add_argument('--root', default=str(Path(__file__).resolve().parents[2] / 'data' / 'recipe_images'), help='Pfad zum Ordner recipe_images')
    p.add_argument('--max-images', type=int, default=2, help='1-3 Fotos pro Rezept (Standard 2)')
    p.add_argument('--limit', type=int, default=0, help='Nur die ersten N Rezepte herunterladen (0=alle)')
    p.add_argument('--only', type=str, default='', help='Eine bestimmte Rezept-ID verarbeiten')
    p.add_argument('--min-score', type=float, default=70, help='Mindestzuverlässigkeit des Dateinamens (Standard 70)')
    p.add_argument('--delay', type=float, default=0.55, help='Pause zwischen Suchabfragen in Sekunden')
    p.add_argument('--dry-run', action='store_true', help='Nur geplante Suchen auflisten, kein Netzwerk')
    p.add_argument('--retry-empty', action='store_true', help='Auch zuvor erfolglos gesuchte Rezepte neu durchsuchen')
    args = p.parse_args(argv)
    args.max_images = max(1, min(3, args.max_images))
    root = Path(args.root)
    catalog = read_catalog(root)
    recipes = catalog['recipes']
    filtered = [r for r in recipes if not args.only or r['recipe_id'] == args.only]
    if args.limit:
        filtered = filtered[:args.limit]
    if args.only and not filtered:
        sys.exit(f'Rezept-ID nicht gefunden: {args.only}')
    print(f'{len(filtered)} Rezepte, maximal {args.max_images} Fotos/Rezept. Quelle: Wikimedia Commons.')
    if args.dry_run:
        for r in filtered:
            print(r['recipe_id'], '\n ', '\n  '.join(make_queries(r)))
        return 0

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept': 'application/json, image/jpeg, image/png, image/webp;q=0.9, */*;q=0.7'})
    try:
        response = session.get(API, params={'action': 'query', 'meta': 'siteinfo', 'format': 'json'}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f'Wikimedia Commons ist nicht erreichbar: {error}', file=sys.stderr)
        return 1
    empty = failed = downloaded = 0
    used_sources = {img['source_url'] for rec in recipes for img in rec['images'] if img.get('source_url')}
    used_hashes = {img['sha256'] for rec in recipes for img in rec['images'] if img.get('sha256')}
    for i, rec in enumerate(filtered, 1):
        current = {img['source_url'] for img in rec['images'] if img.get('source_url')}
        if len(rec['images']) >= args.max_images:
            print(f'[{i}/{len(filtered)}] {rec["name_de"]}: bereits vorhanden')
            continue
        if rec['status'] == 'no_match' and not args.retry_empty:
            empty += 1
            continue
        found = {}
        try:
            for q in make_queries(rec):
                for item in search(session, q, 960):
                    if item['source_url'] not in current:
                        item['match_score'] = match_score(item['file_title'], rec['name_en'], rec['name_de'], item['description'])
                        if item['match_score'] >= args.min_score:
                            found[item['source_url']] = item
                if len(found) >= args.max_images + 2:
                    break
                time.sleep(args.delay)
            choices = sorted(found.values(), key=lambda item: (-item['match_score'], item['file_title']))
            for candidate in choices:
                if len(rec['images']) >= args.max_images:
                    break
                if candidate['source_url'] in used_sources:
                    continue  # Prevent sharing / duplicating the same photo under different recipe IDs.
                target = root / rec['folder'] / f'image_{len(rec["images"])+1:02d}.jpg'
                try:
                    dims = save_photo(session, candidate, target)
                except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as err:
                    print(f'  Bild übersprungen: {str(err)[:150]}')
                    continue
                if dims['sha256'] in used_hashes:
                    target.unlink()
                    if not any(target.parent.iterdir()):
                        target.parent.rmdir()
                    continue
                rec['images'].append({
                    'image_id': f'{rec["recipe_id"]}-{len(rec["images"])+1:02d}',
                    'path': f'{rec["folder"]}/{target.name}',
                    'match_score': candidate['match_score'],
                    'source_type': 'commons', 'rights_status': 'licensed',
                    'modifications': 'Verkleinert und in JPEG umgewandelt',
                    **{k: v for k, v in candidate.items() if k not in ('download_url', 'description', 'original_width', 'original_height')},
                    **dims,
                })
                downloaded += 1
                current.add(candidate['source_url'])
                used_sources.add(candidate['source_url'])
                used_hashes.add(dims['sha256'])
            rec['status'] = 'downloaded' if rec['images'] else 'no_match'
            if not rec['images']:
                empty += 1
            print(f'[{i}/{len(filtered)}] {rec["name_de"]}: {len(rec["images"])} Fotos')
        except (requests.RequestException, RuntimeError, ValueError, json.JSONDecodeError) as err:
            rec['status'] = 'error'
            rec['last_error'] = str(err)[:250]
            failed += 1
            print(f'[{i}/{len(filtered)}] {rec["name_de"]}: FEHLER {rec["last_error"]}', file=sys.stderr)
        # Persist after EACH recipe: resumable and safe for long processes.
        if any(rec['images'] for rec in recipes):
            write_json(root / 'image_catalog.json', catalog)
            synchronize_locales(root, catalog)
            write_attributions(root, recipes)
        time.sleep(args.delay)

    if any(rec['images'] for rec in recipes):
        synchronize_locales(root, catalog)
        count = write_attributions(root, recipes)
    else:
        count = 0
    print(f'Fertig: {count} Bilddateien für {sum(bool(x["images"]) for x in recipes)} Rezepte.'
          + (' Quellen: recipe_images/IMAGE_ATTRIBUTIONS.csv' if count else ' Keine Bilddateien heruntergeladen.'))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
