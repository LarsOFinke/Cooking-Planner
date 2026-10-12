#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

source scripts/build/ensure-linux-deps.sh
mvn -f backend/pom.xml package
mkdir -p build
cp backend/target/cooking-planner-api-0.1.0.jar build/backend.jar
bash scripts/build/build-wheel.sh

python_bin="${PYTHON_BIN:-python3}"
python_tag="$("$python_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
build_python="$project_root/.build-venv-$python_tag/bin/python"
shopt -s nullglob
wheels=(dist/wheels/cooking_planner_desktop-0.1.0-*.whl)
if (( ${#wheels[@]} != 1 )); then
    echo "Expected one Cooking Planner wheel in dist/wheels" >&2
    exit 1
fi
"$build_python" -m pip install --no-deps --force-reinstall "${wheels[0]}"

runtime_dir="$project_root/build/runtime-linux"
rm -rf -- "$runtime_dir"
jlink --add-modules ALL-MODULE-PATH --strip-debug --no-header-files --no-man-pages --output "$runtime_dir"
mkdir -p dist/linux
"$build_python" -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name CookingPlanner --distpath dist/linux --workpath build/pyinstaller-linux --specpath build \
    --add-binary "$runtime_dir:runtime" \
    --add-data "$project_root/build/backend.jar:." \
    --add-data "$project_root/data:catalogs" \
    scripts/build/frozen_entry.py
echo "Built dist/linux/CookingPlanner"
