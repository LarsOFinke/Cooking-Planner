#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

if [[ -n "${DEV_PYTHON:-}" ]]; then
    dev_python="$DEV_PYTHON"
    managed_venv=false
else
    managed_venv=true
    dev_python="$project_root/.venv-dev-linux/bin/python"
    if [[ ! -x "$dev_python" ]]; then
        python_bin="${PYTHON_BIN:-}"
        if [[ -z "$python_bin" ]]; then
            for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
                if command -v "$candidate" >/dev/null 2>&1; then
                    if "$candidate" -c 'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 14)' >/dev/null 2>&1; then
                        python_bin="$candidate"
                        break
                    fi
                fi
            done
        fi
        if [[ -z "$python_bin" ]]; then
            echo "Python 3.11–3.14 is required. Set PYTHON_BIN or DEV_PYTHON." >&2
            exit 1
        fi
        "$python_bin" -m venv .venv-dev-linux
    fi
fi

if ! "$dev_python" -c 'import kivy, sys; assert (sys.version_info[:2] < (3, 14) and kivy.__version__ == "2.3.1") or (sys.version_info[:2] == (3, 14) and kivy.__version__.startswith("3."))' >/dev/null 2>&1; then
    if [[ "$managed_venv" == false ]]; then
        echo "DEV_PYTHON must point to Python with a compatible Kivy version installed." >&2
        exit 1
    fi
    "$dev_python" scripts/development/install-desktop-deps.py
fi

maven_args=(-f backend/pom.xml -DskipTests package)
if [[ -n "${MAVEN_REPO:-}" ]]; then
    maven_args+=("-Dmaven.repo.local=$MAVEN_REPO")
fi
mvn "${maven_args[@]}"
exec "$dev_python" desktop/main.py
