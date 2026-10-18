#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
export PYTHONPYCACHEPREFIX="$project_root/build/python-cache"

if [[ -n "${DEV_PYTHON:-}" ]]; then
    dev_python="$DEV_PYTHON"
    managed_venv=false
else
    managed_venv=true
    dev_python="$project_root/.venv-dev-linux/bin/python"
    if [[ ! -x "$dev_python" ]]; then
        source scripts/build/linux/ensure-linux-deps.sh
        "$PYTHON_BIN" -m venv .venv-dev-linux
    fi
fi

check_args=()
if [[ "$managed_venv" == true ]]; then
    check_args=(--dev)
fi
if ! "$dev_python" scripts/development/check-python-deps.py "${check_args[@]}"; then
    if [[ "$managed_venv" == false ]]; then
        echo "DEV_PYTHON must point to Python with a compatible Kivy version installed." >&2
        exit 1
    fi
    "$dev_python" scripts/development/install-python-deps.py --dev
fi

PYTHONPATH=src/frontend:src/backend exec "$dev_python" src/frontend/main.py
