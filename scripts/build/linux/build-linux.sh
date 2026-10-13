#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$project_root"

source scripts/build/linux/ensure-linux-deps.sh
progress=("$PYTHON_BIN" scripts/build/common/progress.py)
echo '[1/4] Build Python wheel and dependencies'
bash scripts/build/common/build-wheel.sh

python_tag="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
build_python="$project_root/.build-venv-$python_tag/bin/python"
shopt -s nullglob
wheels=(dist/wheels/cooking_planner-0.1.0-*.whl)
if (( ${#wheels[@]} != 1 )); then
    echo 'Expected one Cooking Planner wheel in dist/wheels' >&2
    exit 1
fi
"${progress[@]}" --step 2 --total 4 --name 'Install app wheel' \
    --log build/logs/linux-wheel-install.log -- \
    "$build_python" -m pip install --no-deps --force-reinstall "${wheels[0]}"
"${progress[@]}" --step 3 --total 4 --name 'Build bundled Linux executable' \
    --log build/logs/linux-executable.log -- \
    "$build_python" -m PyInstaller --noconfirm --onefile --windowed \
    --name CookingPlanner --distpath dist/linux --workpath build/pyinstaller-linux --specpath build \
    --collect-submodules sqlalchemy.dialects.sqlite --collect-submodules uvicorn \
    --add-data "$project_root/data:catalogs" scripts/build/common/frozen_entry.py
"${progress[@]}" --step 4 --total 4 --name 'Build Linux AppImage' \
    --log build/logs/linux-appimage.log -- bash scripts/build/linux/package-linux.sh
