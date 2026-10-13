"""Keep production classes in one matching PascalCase Python file each."""

import ast
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
PASCAL_CASE = re.compile(r'[A-Z][A-Za-z0-9]*\Z')


def main() -> int:
    failures = []
    for base in (ROOT / 'src' / 'frontend', ROOT / 'src' / 'backend', ROOT / 'scripts'):
        for path in base.rglob('*.py'):
            if '__pycache__' in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            if classes and (len(classes) != 1 or path.stem != classes[0] or
                            not PASCAL_CASE.fullmatch(path.stem)):
                failures.append(f'{path.relative_to(ROOT)}: {classes}')
    if failures:
        print('Production class files must contain one class with the same PascalCase name:', file=sys.stderr)
        print('\n'.join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
