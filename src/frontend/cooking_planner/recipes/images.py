"""Resolve verified local recipe photos and their attribution records."""

import csv
import re
from pathlib import Path

from cooking_planner.paths import catalog_directory

PHOTO_NAME = re.compile(r'image_\d{2}\.(?:jpg|jpeg|png|webp)', re.IGNORECASE)


def image_file(recipe_id: str, reference: str) -> Path | None:
    """Reject arbitrary paths from API data and resolve a local recipe image."""
    if not recipe_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in recipe_id):
        return None
    prefix = f"recipe_images/{recipe_id}/"
    if not reference.startswith(prefix):
        return None
    filename = reference[len(prefix):]
    if not PHOTO_NAME.fullmatch(filename):
        return None
    target = catalog_directory() / "recipe_images" / recipe_id / filename
    return target if target.is_file() else None


def attributions() -> dict[str, dict]:
    source = catalog_directory() / "recipe_images" / "IMAGE_ATTRIBUTIONS.csv"
    if not source.is_file():
        return {}
    with source.open(encoding="utf-8-sig", newline="") as file:
        return {"recipe_images/" + row["image_path"]: row for row in csv.DictReader(file)}
