#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$project_root"

binary="$project_root/dist/linux/CookingPlanner"
[[ -x "$binary" ]] || { echo "Build the Linux executable first: make compile-linux" >&2; exit 1; }

case "$(uname -m)" in
    x86_64) arch=x86_64; sha=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0 ;;
    aarch64) arch=aarch64; sha=f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158 ;;
    *) echo "AppImage packaging supports x86_64 and aarch64 only" >&2; exit 1 ;;
esac

tool="${APPIMAGETOOL:-$project_root/build/tools/appimagetool-$arch.AppImage}"
if [[ -z "${APPIMAGETOOL:-}" && ! -f "$tool" ]]; then
    mkdir -p build/tools
    curl -fL "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-$arch.AppImage" \
        -o "$tool.tmp"
    printf '%s  %s\n' "$sha" "$tool.tmp" | sha256sum -c -
    mv "$tool.tmp" "$tool"
fi
if [[ -z "${APPIMAGETOOL:-}" ]]; then
    printf '%s  %s\n' "$sha" "$tool" | sha256sum -c -
fi
chmod +x "$tool"

appdir="$project_root/build/CookingPlanner.AppDir"
rm -rf -- "$appdir"
mkdir -p "$appdir/usr/bin"
cp "$binary" "$appdir/usr/bin/CookingPlanner"
cp scripts/build/linux/cooking-planner.svg "$appdir/cooking-planner.svg"
cp scripts/build/linux/cooking-planner.desktop "$appdir/cooking-planner.desktop"
cp scripts/build/linux/AppRun "$appdir/AppRun"
chmod +x "$appdir/AppRun"
ARCH="$arch" APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream "$appdir" \
    "$project_root/dist/linux/CookingPlanner-$arch.AppImage"
echo "Built dist/linux/CookingPlanner-$arch.AppImage"
