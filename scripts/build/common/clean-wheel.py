"""Remove stale setuptools output before building the current source tree."""

from pathlib import Path
from shutil import rmtree

ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT / 'build' / 'lib', ROOT / 'src' / 'cooking_planner_desktop.egg-info',
             ROOT / 'cooking_planner.egg-info'):
    if path.is_dir():
        rmtree(path)
for path in (ROOT / 'build').glob('bdist.*'):
    if path.is_dir():
        rmtree(path)
for path in (ROOT / 'dist' / 'wheels').glob('cooking_planner-*.whl'):
    path.unlink()
