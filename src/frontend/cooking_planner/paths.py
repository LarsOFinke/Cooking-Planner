"""Locations shared by local storage and recipe images."""

import os
import sys
from pathlib import Path


def on_android() -> bool:
    return 'ANDROID_ARGUMENT' in os.environ


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1 if on_android() else 3]


def catalog_directory() -> Path:
    default = bundle_root() / ("catalogs" if getattr(sys, "frozen", False) or on_android() else "data")
    return Path(os.getenv("COOKING_PLANNER_CATALOG_DIR", default))
