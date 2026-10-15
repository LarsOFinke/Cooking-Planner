#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$project_root"

if [[ "$(uname -s)" != Linux ]]; then
    echo 'Android APK builds require Linux (or WSL2).' >&2
    exit 1
fi
python_bin="${ANDROID_PYTHON:-python3.14}"
"$python_bin" -c 'import sys, venv; assert sys.version_info[:2] == (3, 14)' || {
    echo 'ANDROID_PYTHON must be Python 3.14 with venv support.' >&2
    exit 1
}
for required in git zip unzip java javac autoconf automake pkg-config cmake rustup rustc cargo; do
    command -v "$required" >/dev/null 2>&1 || {
        echo "Missing Android build prerequisite: $required. See docs/ANDROID_BUILD.md." >&2
        exit 1
    }
done
java_version="$(java -version 2>&1 | head -n 1)"
if [[ "$java_version" != *'17.'* ]]; then
    echo "Android builds require JDK 17; active version: $java_version" >&2
    exit 1
fi

venv="$project_root/.build-venv-android"
# python-for-android installs host tools with pip --user; the user site must be visible.
"$python_bin" -m venv --system-site-packages "$venv"
"$venv/bin/python" -m pip install -r scripts/build/android/requirements-host.txt
export PATH="$venv/bin:$PATH"
"$venv/bin/python" scripts/build/android/stage.py

build_dir="$project_root/build/android"
cp scripts/build/android/buildozer.spec "$build_dir/buildozer.spec"
cd "$build_dir"
"$venv/bin/buildozer" -v android debug

shopt -s nullglob
artifacts=(bin/*-debug.apk)
if (( ${#artifacts[@]} != 1 )); then
    echo "Expected one debug APK, found ${#artifacts[@]} in $build_dir/bin" >&2
    exit 1
fi
mkdir -p "$project_root/dist/android"
cp "${artifacts[0]}" "$project_root/dist/android/CookingPlanner-arm64-v8a-debug.apk"
echo 'Built dist/android/CookingPlanner-arm64-v8a-debug.apk'
