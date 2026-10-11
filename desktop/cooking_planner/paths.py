"""Locations shared by the backend launcher and local recipe images."""

import os
import sys
from pathlib import Path


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def catalog_directory() -> Path:
    default = bundle_root() / ("catalogs" if getattr(sys, "frozen", False) else "data")
    return Path(os.getenv("COOKING_PLANNER_CATALOG_DIR", default))
