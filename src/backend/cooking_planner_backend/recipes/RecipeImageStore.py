"""Validate and store user recipe photos outside the read-only catalog."""

import base64
import binascii
import hashlib
import re
from pathlib import Path


IMAGE_NAME = re.compile(r'image_0[1-3](?:-[0-9a-f]{12})?\.(?:png|jpg|jpeg|webp)\Z')
UPLOADED_NAME = re.compile(r'image_0[1-3]-[0-9a-f]{12}\.(?:png|jpg|jpeg|webp)\Z')
MAX_IMAGE_BYTES = 8_000_000


def image_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) > 24 and data[12:16] == b'IHDR':
        return 'png'
    if data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'):
        return 'jpeg'
    if (data.startswith(b'RIFF') and data[8:12] == b'WEBP' and
            int.from_bytes(data[4:8], 'little') + 8 == len(data)):
        return 'webp'
    raise ValueError('Choose a valid PNG, JPEG, or WebP image')


class RecipeImageStore:
    def __init__(self, data_dir: Path, catalog_dir: Path):
        self.user_root = Path(data_dir) / 'recipe_images'
        self.catalog_root = Path(catalog_dir) / 'recipe_images'

    def _user_file(self, recipe_id, reference):
        prefix = f'recipe_images/{recipe_id}/'
        if not reference.startswith(prefix):
            raise ValueError('Image reference belongs to another recipe')
        name = reference[len(prefix):]
        if not IMAGE_NAME.fullmatch(name):
            raise ValueError('Invalid recipe image reference')
        return self.user_root / recipe_id / name

    def stage(self, recipe_id, references, uploads):
        if not isinstance(uploads, list) or len(uploads) > 3:
            raise ValueError('Choose up to three recipe images')
        created = []
        uploaded = set()
        try:
            for item in uploads:
                if not isinstance(item, dict):
                    raise ValueError('Invalid image upload')
                reference = item.get('reference')
                if not isinstance(reference, str) or reference not in references or reference in uploaded:
                    raise ValueError('Image upload does not match the recipe')
                target = self._user_file(recipe_id, reference)
                if not UPLOADED_NAME.fullmatch(target.name):
                    raise ValueError('Uploaded images need a unique image name')
                encoded = item.get('data')
                if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES * 4 // 3) + 8:
                    raise ValueError('Image is too large')
                try:
                    data = base64.b64decode(encoded, validate=True)
                except binascii.Error as error:
                    raise ValueError('Invalid image upload') from error
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError('Image is too large')
                kind = image_type(data)
                if target.suffix.lower().lstrip('.') not in (('jpg', 'jpeg') if kind == 'jpeg' else (kind,)):
                    raise ValueError('Image extension does not match its content')
                if self.user_root.is_symlink() or target.parent.is_symlink():
                    raise ValueError('Invalid image destination')
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if not target.parent.resolve().is_relative_to(self.user_root.parent.resolve()):
                    raise ValueError('Invalid image destination')
                try:
                    with target.open('xb') as output:
                        output.write(data)
                except FileExistsError as error:
                    raise ValueError('Image already exists; select it again') from error
                created.append(target)
                uploaded.add(reference)
            for reference in references:
                target = self._user_file(recipe_id, reference)
                bundled = self.catalog_root / recipe_id / target.name
                source = target if UPLOADED_NAME.fullmatch(target.name) else bundled
                if reference not in uploaded and not source.is_file():
                    raise ValueError('Selected recipe image is missing')
            digests = set()
            for reference in references:
                target = self._user_file(recipe_id, reference)
                path = target if UPLOADED_NAME.fullmatch(target.name) else self.catalog_root / recipe_id / target.name
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').digest()
                if digest in digests:
                    raise ValueError('The same image was selected more than once')
                digests.add(digest)
        except BaseException:
            self.remove(created)
            raise
        return created

    @staticmethod
    def remove(paths):
        for path in paths:
            path.unlink(missing_ok=True)

    def prune(self, recipe_id, before, after):
        for reference in set(before) - set(after):
            target = self._user_file(recipe_id, reference)
            if UPLOADED_NAME.fullmatch(target.name):
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
