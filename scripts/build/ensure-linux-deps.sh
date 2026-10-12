#!/usr/bin/env bash
# Source this file before building; it exports PYTHON_BIN and JAVA_HOME.

supports_python() {
    "$1" -c 'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 14)' >/dev/null 2>&1
}

find_python() {
    local candidate
    for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && supports_python "$candidate"; then
            command -v "$candidate"
            return
        fi
    done
    return 1
}

find_java21() {
    local home version
    for home in "${JAVA_HOME:-}" /usr/lib/jvm/*; do
        [[ -n "$home" && -x "$home/bin/java" && -x "$home/bin/jlink" ]] || continue
        version="$("$home/bin/jlink" --version 2>/dev/null)"
        if [[ "$version" =~ ^21([.]|$) ]]; then
            printf '%s\n' "$home"
            return
        fi
    done
    return 1
}

venv_works() {
    local probe
    probe="$(mktemp -d)"
    if "$PYTHON_BIN" -m venv "$probe" >/dev/null 2>&1; then
        rm -rf -- "$probe"
        return 0
    fi
    rm -rf -- "$probe"
    return 1
}

apt_update() {
    if [[ "$(id -u)" -eq 0 ]]; then
        apt-get update
    else
        if ! command -v sudo >/dev/null 2>&1; then
            echo "sudo is required to install missing build tools: $*" >&2
            return 1
        fi
        sudo apt-get update
    fi
}

apt_install() {
    if [[ "$apt_updated" != true ]]; then
        apt_update "$@"
    fi
    if [[ "$(id -u)" -eq 0 ]]; then
        apt-get install -y --no-install-recommends "$@"
    else
        sudo apt-get install -y --no-install-recommends "$@"
    fi
}

if [[ -n "${PYTHON_BIN:-}" ]]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1 || ! supports_python "$PYTHON_BIN"; then
        echo "PYTHON_BIN must point to Python 3.11–3.14." >&2
        return 1
    fi
else
    PYTHON_BIN="$(find_python || true)"
fi

packages=()
apt_updated=false
if ! command -v mvn >/dev/null 2>&1; then
    packages+=(maven)
fi
if ! java_home="$(find_java21)"; then
    packages+=(openjdk-21-jdk)
fi
if [[ -n "$PYTHON_BIN" ]] && ! venv_works; then
    python_version="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    packages+=("python${python_version}-venv")
fi

if [[ -z "$PYTHON_BIN" || ${#packages[@]} -gt 0 ]]; then
    # Other Linux distributions can build when their tools are already present.
    source /etc/os-release
    if [[ "$ID" != ubuntu && "$ID" != debian && " ${ID_LIKE:-} " != *" debian "* ]]; then
        echo "Install Maven, JDK 21, and Python 3.11–3.14 with venv, then rerun the build." >&2
        return 1
    fi
    if [[ -z "$PYTHON_BIN" ]]; then
        # Refresh package lists before choosing the newest supported interpreter.
        apt_update "Python 3.11–3.14"
        apt_updated=true
        selected_python_package=""
        for python_version in 3.14 3.13 3.12 3.11; do
            if apt-cache show "python${python_version}" >/dev/null 2>&1 &&
               apt-cache show "python${python_version}-venv" >/dev/null 2>&1; then
                packages+=("python${python_version}" "python${python_version}-venv")
                selected_python_package="$python_version"
                break
            fi
        done
        if [[ -z "$selected_python_package" ]]; then
            echo "No supported Python 3.11–3.14 package is available from APT." >&2
            return 1
        fi
    fi
    echo "Installing missing Linux build tools: ${packages[*]}"
    apt_install "${packages[@]}"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(find_python || true)"
fi
if [[ -z "$PYTHON_BIN" ]] || ! venv_works; then
    echo "Python 3.11–3.14 with venv and pip is required to build Cooking Planner." >&2
    return 1
fi
if ! command -v mvn >/dev/null 2>&1; then
    echo "Maven is required to build Cooking Planner." >&2
    return 1
fi
java_home="$(find_java21)" || {
    echo "JDK 21 with jlink is required to build Cooking Planner." >&2
    return 1
}
export PYTHON_BIN JAVA_HOME="$java_home"
export PATH="$JAVA_HOME/bin:$PATH"
