"""Check pinned runtime requirements and optionally the development tools."""

import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

MARKER = re.compile(r'''python_version\s*(<|>=)\s*['"](\d+\.\d+)['"]''')


def active_requirement(line: str) -> str | None:
    spec, separator, marker = line.partition(';')
    if separator:
        match = MARKER.fullmatch(marker.strip())
        if not match:
            raise ValueError(f'Unsupported requirement marker: {marker}')
        current = sys.version_info[:2]
        target = tuple(map(int, match.group(2).split('.')))
        if not (current < target if match.group(1) == '<' else current >= target):
            return None
    return spec.strip()


def main() -> int:
    if not (3, 11) <= sys.version_info[:2] <= (3, 14):
        return 1
    source = Path(__file__).resolve().parents[2] / 'src'
    files = ['requirements.txt']
    if '--dev' in sys.argv[1:]:
        files.append('requirements-dev.txt')
    for file in files:
        for line in (source / file).read_text(encoding='utf-8').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            spec = active_requirement(line)
            if spec is None:
                continue
            name, expected = spec.split('==', 1)
            try:
                if version(name.strip()) != expected.strip():
                    return 1
            except PackageNotFoundError:
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
