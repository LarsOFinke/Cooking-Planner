#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

quality_python="${QUALITY_PYTHON:-}"
if [[ -z "$quality_python" ]]; then
    if [[ -x "$project_root/.venv-dev-linux/bin/python" ]]; then
        quality_python="$project_root/.venv-dev-linux/bin/python"
    else
        quality_python=python3
    fi
fi
"$quality_python" -m compileall -q desktop/cooking_planner desktop/tests scripts
if command -v ruff >/dev/null 2>&1; then
    ruff check desktop scripts
elif "$quality_python" -m ruff --version >/dev/null 2>&1; then
    "$quality_python" -m ruff check desktop scripts
else
    echo "Ruff is required for make quality. Install desktop/requirements-dev.txt in a Python environment." >&2
    exit 1
fi
git diff --check
"$quality_python" scripts/quality/python-coverage.py
make test
