"""Validate the supported local photo formats and return their content digest."""

import hashlib
import re
import struct
from pathlib import Path

PHOTO_NAME = re.compile(r'image_([0-9]{2})\.(jpg|jpeg|png|webp)')


def check_photo(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 1024:
        raise ValueError(f'Empty or tiny image: {path}')
    suffix = path.suffix.lower()
    if suffix in ('.jpg', '.jpeg'):
        valid = data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9')
    elif suffix == '.png':
        valid = data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-32:]
    elif suffix == '.webp':
        valid = (data.startswith(b'RIFF') and data[8:12] == b'WEBP'
                 and struct.unpack('<I', data[4:8])[0] + 8 == len(data))
    else:
        valid = False
    if not valid:
        raise ValueError(f'Image content does not match its extension: {path}')
    return hashlib.sha256(data).hexdigest()
