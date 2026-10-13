#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$project_root"

python_bin="${PYTHON_BIN:-python3}"
python_tag="$("$python_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
build_venv="$project_root/.build-venv-$python_tag"
build_python="$build_venv/bin/python"
progress=("$python_bin" scripts/build/common/progress.py)
if [[ ! -x "$build_python" ]]; then
    "${progress[@]}" --step 1 --total 4 --name 'Create build environment' \
        --log build/logs/wheel-venv.log -- "$python_bin" -m venv "$build_venv"
else
    echo '[1/4] Build environment reused'
fi
"${progress[@]}" --step 2 --total 4 --name 'Install build tools' \
    --log build/logs/wheel-tools.log -- "$build_python" -m pip install -r src/requirements-build.txt
"${progress[@]}" --step 3 --total 4 --name 'Install app dependencies' \
    --log build/logs/wheel-dependencies.log -- "$build_python" scripts/development/install-python-deps.py
"$build_python" scripts/build/common/clean-wheel.py
"${progress[@]}" --step 4 --total 4 --name 'Build Python wheel' \
    --log build/logs/wheel-package.log -- "$build_python" -m build --wheel --no-isolation --outdir dist/wheels .
