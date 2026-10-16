"""Check that a development environment matches the pinned runtime requirements."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys


def main() -> int:
    if not (3, 11) <= sys.version_info[:2] <= (3, 14):
        return 1
    requirements = Path(__file__).resolve().parents[2] / 'src' / 'requirements.txt'
    for line in requirements.read_text(encoding='utf-8').splitlines():
        spec, _, marker = line.partition(';')
        if marker:
            needs_314 = '>=' in marker
            if needs_314 != (sys.version_info[:2] >= (3, 14)):
                continue
        name, expected = spec.strip().split('==', 1)
        try:
            if version(name) != expected:
                return 1
        except PackageNotFoundError:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
