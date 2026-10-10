import re
from pathlib import Path


def locale_from_filename(path: Path) -> str:
    match = re.fullmatch(r"recipes_([a-z]{2})\.json", path.name, re.IGNORECASE)
    if not match:
        raise ValueError("Use a filename like recipes_en.json or recipes_de.json")
    return match.group(1).lower()
