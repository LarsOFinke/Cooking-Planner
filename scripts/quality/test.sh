#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
quality_python="${QUALITY_PYTHON:-}"
if [[ -z "$quality_python" ]]; then
    quality_python="$project_root/.venv-dev-linux/bin/python"
fi
PYTHONPATH=src/frontend:src/backend "$quality_python" -m unittest discover -s src/tests
