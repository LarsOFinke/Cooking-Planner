#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

bash scripts/build/linux/build-linux.sh

bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$bin_dir"
arch="$(uname -m)"
install -m 755 "dist/linux/CookingPlanner-$arch.AppImage" "$bin_dir/.cooking-planner-new"
mv -f "$bin_dir/.cooking-planner-new" "$bin_dir/cooking-planner"
echo "Installed $bin_dir/cooking-planner"
if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
    echo "Add $bin_dir to PATH to run cooking-planner from the terminal."
fi
