#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

python_bin="${PYTHON_BIN:-python3}"
python_tag="$("$python_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
build_venv="$project_root/.build-venv-$python_tag"
"$python_bin" -m venv "$build_venv"
build_python="$build_venv/bin/python"
"$build_python" -m pip install -r desktop/requirements-build.txt
"$build_python" scripts/development/install-desktop-deps.py
"$build_python" -m build --wheel --no-isolation --outdir dist/wheels .
