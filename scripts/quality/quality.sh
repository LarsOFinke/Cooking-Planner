#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
export PYTHONPYCACHEPREFIX="$project_root/build/python-cache"

quality_python="${QUALITY_PYTHON:-}"
if [[ -z "$quality_python" ]]; then
    if [[ -x "$project_root/.venv-dev-linux/bin/python" ]]; then
        quality_python="$project_root/.venv-dev-linux/bin/python"
    else
        quality_python=python3
    fi
fi
"$quality_python" -m compileall -q src/frontend/cooking_planner src/backend/cooking_planner_backend src/tests scripts
"$quality_python" scripts/quality/check-class-files.py
if "$quality_python" -m ruff --version >/dev/null 2>&1; then
    "$quality_python" -m ruff check src scripts
else
    echo "Ruff is required for make quality. Install src/requirements-dev.txt in a Python environment." >&2
    exit 1
fi
git diff --check
"$quality_python" scripts/quality/python-coverage.py
