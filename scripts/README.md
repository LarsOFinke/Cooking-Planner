# Script entry points

Run commands from the repository root. `make help` lists the supported shortcuts.

| Area | Entry point | Owns |
| --- | --- | --- |
| Development | `make dev` | A managed desktop environment and source launch |
| Quality | `make test`, `make quality` | Python tests, Ruff, coverage, and source checks |
| Linux | `make compile-linux` | Wheel, PyInstaller executable, AppImage |
| Windows | `make compile-windows` on Windows | Wheel, PyInstaller directory, Inno installer |
| Android (manual, paused) | `make compile-android` on Linux | Staged source, debug APK, APK manifest check |
| Images | `python3 scripts/images/import_local_recipe_images.py` | Bundled image references and credits |

`pyproject.toml` owns the application version. Both desktop builders clear their previous
Cooking Planner wheels before building and require exactly one wheel matching that
version. The Windows builder passes the version to Inno Setup; Android staging writes
it into the generated Buildozer spec. Build outputs, logs, and cached tools live under
`build/` or `dist/` and are generated files.

The image importer validates both locales and all images before changing catalog
files. It keeps backups in `data/.image-import-recovery/` while writing; a later import
restores those files if the previous process was interrupted. After changing bundled
images, run `python3 scripts/images/verify_recipe_images.py`. Importing images remains
a separate maintenance action; CI verifies the bundled references before packaging.

`make quality` covers Python code and tests. CI also checks Bash scripts with
ShellCheck and parses PowerShell scripts on Windows. A passing quality check does not
verify native packages or Android device behavior; use each target platform's build
and runtime checks for that.

The current CI package jobs build only Linux and Windows artifacts. Android build
scripts and the manual command remain in the repository for later device testing.
