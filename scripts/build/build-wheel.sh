#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

python_bin="${PYTHON_BIN:-python3}"
"$python_bin" -m venv .build-venv
build_python="$project_root/.build-venv/bin/python"
"$build_python" -m pip install -r desktop/requirements-build.txt
"$build_python" scripts/development/install-desktop-deps.py
"$build_python" -m build --wheel --no-isolation --outdir dist/wheels .
