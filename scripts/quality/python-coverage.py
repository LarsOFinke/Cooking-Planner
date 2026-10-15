"""Run Python tests and enforce 60% coverage for UI and backend separately."""

import io
import os
import sys
import unittest
from pathlib import Path

from coverage import Coverage

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (ROOT / 'src' / 'frontend' / 'cooking_planner',
           ROOT / 'src' / 'backend' / 'cooking_planner_backend')
sys.path.insert(0, str(ROOT / 'src' / 'frontend'))
sys.path.insert(0, str(ROOT / 'src' / 'backend'))
os.environ.setdefault('KIVY_NO_FILELOG', '1')


def run_tests():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'src' / 'tests'))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    if not result.wasSuccessful():
        print(output.getvalue(), file=sys.stderr)
    return result


def main() -> int:
    if sys.platform == 'linux' and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('Desktop coverage requires a display.', file=sys.stderr)
        return 2
    try:
        import kivy  # noqa: F401
    except ImportError:
        print('Desktop coverage requires Kivy. Run make dev first.', file=sys.stderr)
        return 2
    coverage = Coverage(source=[str(source) for source in SOURCES], data_file=None)
    coverage.start()
    try:
        result = run_tests()
    finally:
        coverage.stop()
    if not result.wasSuccessful():
        print(f'{len(result.failures)} failures, {len(result.errors)} errors', file=sys.stderr)
        return 1
    good = True
    for source in SOURCES:
        covered = total = 0
        for path in sorted(source.rglob('*.py')):
            _, statements, _, missing, _ = coverage.analysis2(str(path))
            matched = len(statements) - len(missing)
            covered += matched
            total += len(statements)
            print(f'{source.name}/{path.relative_to(source)}: {matched}/{len(statements)}')
        ratio = covered / total if total else 0
        print(f'{source.name} line coverage: {covered}/{total} ({ratio:.1%})')
        good &= ratio >= 0.60
    print(f'{result.testsRun} tests')
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
