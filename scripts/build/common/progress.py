"""Show build stages while retaining complete tool output for failures."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', type=int, required=True)
    parser.add_argument('--total', type=int, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not 1 <= args.step <= args.total:
        parser.error('provide a command and a valid step/total pair')

    title = f'[{args.step}/{args.total}] {args.name}'
    print(title, flush=True)
    if os.environ.get('COOKING_PLANNER_BUILD_VERBOSE') == '1':
        return subprocess.run(command, check=False).returncode

    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open('w', encoding='utf-8', errors='replace') as output:
        try:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
        except OSError as error:
            print(f'{args.name} could not start: {error}', file=sys.stderr)
            return 1
        frames = '|/-\\'
        frame = 0
        while process.poll() is None:
            if sys.stdout.isatty():
                print(f'\r{title}  {frames[frame % len(frames)]}', end='', flush=True)
                frame += 1
            time.sleep(0.15)
        result = process.returncode

    if sys.stdout.isatty():
        print('\r\x1b[2K', end='')
    if result == 0:
        print(f'{title} done', flush=True)
        return 0
    print(f'{title} failed (exit {result}). Full log: {args.log}', file=sys.stderr)
    lines = args.log.read_text(encoding='utf-8', errors='replace').splitlines()
    for line in lines[-60:]:
        print(line, file=sys.stderr)
    return result if result > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
