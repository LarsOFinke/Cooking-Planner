"""Print the version declared in pyproject.toml for package builders."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def project_version(root: Path = ROOT) -> str:
    with (root / 'pyproject.toml').open('rb') as file:
        return tomllib.load(file)['project']['version']


if __name__ == '__main__':
    print(project_version())
