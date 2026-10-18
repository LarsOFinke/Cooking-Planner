"""Create the self-contained source directory consumed by Buildozer."""

import re
import sys
from pathlib import Path
from shutil import copy2, copytree, rmtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from project_version import project_version

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / 'build' / 'android' / 'source'


def stage(root: Path = ROOT, destination: Path = STAGE) -> Path:
    if destination.exists():
        rmtree(destination)
    destination.mkdir(parents=True)
    copy2(root / 'src' / 'frontend' / 'main.py', destination / 'main.py')
    copytree(root / 'src' / 'frontend' / 'cooking_planner', destination / 'cooking_planner',
             ignore=lambda _, names: {'__pycache__'} & set(names))
    copytree(root / 'src' / 'backend' / 'cooking_planner_backend', destination / 'cooking_planner_backend',
             ignore=lambda _, names: {'__pycache__'} & set(names))
    catalogs = destination / 'catalogs'
    catalogs.mkdir()
    for source in sorted((root / 'data').glob('recipes_??.json')):
        copy2(source, catalogs / source.name)
    if not list(catalogs.glob('recipes_??.json')):
        raise RuntimeError('No recipe catalogs were found for the Android package')
    copytree(root / 'data' / 'recipe_images', catalogs / 'recipe_images')
    spec = (root / 'scripts' / 'build' / 'android' / 'buildozer.spec').read_text(encoding='utf-8')
    spec, replacements = re.subn(r'(?m)^version = .*$', f'version = {project_version(root)}', spec)
    if replacements != 1:
        raise ValueError('Expected one Android package version in buildozer.spec')
    (destination.parent / 'buildozer.spec').write_text(spec, encoding='utf-8')
    return destination


if __name__ == '__main__':
    print(f'Android sources staged at {stage()}')
