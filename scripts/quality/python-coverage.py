"""Run desktop tests and enforce a 60% source-line coverage floor."""

import io
import os
import sys
import trace
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'desktop' / 'cooking_planner'
sys.path.insert(0, str(ROOT / 'desktop'))
os.environ.setdefault('KIVY_NO_FILELOG', '1')


def executable_lines(code: types.CodeType) -> set[int]:
    lines = {line for _, _, line in code.co_lines() if line is not None}
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            lines.update(executable_lines(constant))
    return lines


def run_tests():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'desktop' / 'tests'))
    return unittest.TextTestRunner(stream=io.StringIO()).run(suite)


def main() -> int:
    if sys.platform == 'linux' and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('Desktop coverage requires a display.', file=sys.stderr)
        return 2
    try:
        import kivy  # noqa: F401
    except ImportError:
        print('Desktop coverage requires Kivy. Run make dev first.', file=sys.stderr)
        return 2
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.base_prefix])
    result = tracer.runfunc(run_tests)
    if not result.wasSuccessful():
        print(f'{len(result.failures)} failures, {len(result.errors)} errors', file=sys.stderr)
        return 1
    counts = tracer.results().counts
    hits = {}
    for (filename, line), count in counts.items():
        if count:
            hits.setdefault(Path(filename).resolve(), set()).add(line)
    covered = total = 0
    for path in sorted(SOURCE.rglob('*.py')):
        source_lines = executable_lines(compile(path.read_text(encoding='utf-8'), str(path), 'exec'))
        matched = len(source_lines & hits.get(path.resolve(), set()))
        covered += matched
        total += len(source_lines)
        print(f'{path.relative_to(SOURCE)}: {matched}/{len(source_lines)}')
    ratio = covered / total if total else 0
    print(f'Desktop line coverage: {covered}/{total} ({ratio:.1%}); {result.testsRun} tests')
    return 0 if ratio >= 0.60 else 1


if __name__ == '__main__':
    raise SystemExit(main())
