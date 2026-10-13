#!/usr/bin/env bash
# Source this file before building; it exports PYTHON_BIN.

supports_python() {
    "$1" -c 'import sys, venv, ensurepip; assert (3, 11) <= sys.version_info[:2] <= (3, 14)' >/dev/null 2>&1
}

if [[ -n "${PYTHON_BIN:-}" ]]; then
    supports_python "$PYTHON_BIN" || { echo 'PYTHON_BIN must be Python 3.11–3.14 with venv.' >&2; return 1; }
else
    for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && supports_python "$candidate"; then
            PYTHON_BIN="$(command -v "$candidate")"
            break
        fi
    done
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
    echo 'Install Python 3.11–3.14 with venv, then rerun the build.' >&2
    return 1
fi
export PYTHON_BIN
