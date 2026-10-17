# Cooking Planner

Cooking Planner is a local Windows/Linux desktop app for browsing English and German recipes, planning meals, estimating costs, and preparing a shopping list. The Kivy app calls local Python services directly. SQLAlchemy stores ingredient names and prices in SQLite; no network service or firewall exception is needed.

The source tree keeps the UI in `src/frontend/cooking_planner`, local services and data logic in `src/backend/cooking_planner_backend`, and tests in `src/tests`. Build scripts live in `scripts/build/linux`, `scripts/build/windows`, `scripts/build/android`, and `scripts/build/common`; development, quality, image, and install scripts have their own directories. See the [script entry points](scripts/README.md) for ownership and checks.

## Run and build

Install Python 3.11–3.14, then use these commands from the repository root:

| Purpose | Command | Result |
| --- | --- | --- |
| Source run | `make dev` | Installs missing Python packages and opens the app |
| Tests | `make test` | Runs frontend and backend Python tests |
| Full checks | `make quality` | Syntax, Ruff, tests, and separate 60% coverage floors |
| Linux distribution | `make compile-linux` | `dist/linux/CookingPlanner-<arch>.AppImage` |
| Windows distribution | `make compile-windows` on Windows | `dist/windows/CookingPlanner-Setup.exe` |
| Android debug package | `make compile-android` on Linux | `dist/android/CookingPlanner-arm64-v8a-debug.apk` |

`make linux`, `make windows`, and `make android` are aliases. `make help` lists the main commands. On Windows without GNU Make, use `scripts/development/dev-windows.ps1` or `scripts/build/windows/build-windows.ps1` directly. The first source run needs network access to install Python packages. Set `PYTHON_BIN` to choose a supported interpreter or `DEV_PYTHON` to use an existing environment. The Android build prerequisites and device checks are in [Android build](docs/ANDROID_BUILD.md).

GitHub Actions runs the quality checks on pull requests and builds Linux, Windows, and Android packages on pushes to `main` or from **Actions → Build packages → Run workflow**. Download the AppImage, Windows installer, or Android debug APK from the completed run's **Artifacts** section. These artifacts are development builds; the Android APK is not a signed store release. The workflows build on their target operating systems, but installing and opening the resulting packages on a device remains a separate release check.

The distribution builds bundle Python, Kivy, the backend, and the recipe catalogs. Users need no Python installation. Build each installer on its target operating system. The Linux AppImage runs directly after `chmod +x`; it can be copied to `~/.local/bin/cooking-planner` for a terminal command. The Windows installer installs to the current user's Programs directory and creates a Start menu shortcut. `scripts/install/` contains optional build-and-install shortcuts for the build machine.

The Linux builder uses the official checksum-verified `appimagetool` 1.9.1 release, or a tool supplied through `APPIMAGETOOL`. The Windows builder uses Inno Setup 6 and can obtain it through WinGet. Builds retain logs in `build/logs/`. The AppImage and Windows installer need target-system runtime checks before release. The Android command builds a debug APK; signing and device validation are separate release steps. iOS packaging remains a later phase.

## Features and data

The Explore view has filters, recipe details, cooking steps, and a local image gallery. The recipe tab shows one step at a time with Previous and Next controls. Cooking steps and their measured, per-person ingredients can be checked off; the current step and checks last for the current app session. Week stores meals by day and slot with servings. Shopping adds ingredients only from meals explicitly chosen there; editing Week does not add shopping items. You can import a chosen day's meals, select meals and ingredients, add custom items, clear the entire weekly list, mark items Bought, and save prices. The open cost estimate excludes bought items. Admin edits recipes and ingredient translations across the available languages; new recipe IDs include the selected country code when available, so dishes with the same name from different countries stay distinct. The backend blocks recipes with the same name, country, and region. Ingredients are chosen from the catalog, cooking steps select ingredients by name and quantity, and recipe photos are chosen through a previewable file picker. Ingredient names are edited in the ingredient catalog. Reference prices per quantity drive recipe and weekly cost estimates. The scale menu saves 100–200% UI scaling in `client.cfg`.

Bundled catalogs are `data/recipes_<language>.json`. The supplied English and German catalogs each have 586 recipes with shared IDs. They are read only. Recipe additions, edits, omissions, and deletion markers go to `recipe-edits.json` in the user data directory; photos selected in Admin go to its `recipe_images/<recipe-id>/` folder. Meal plans go to `plans.json`; ingredient names and prices go to `cooking-planner.db`; shopping choices and custom items go to `shopping.json`. The shopping file also queues unfinished SQLite writes for retry after interruption. Recipe edits use a recovery journal, while ingredient translations remain owned by the ingredient catalog in SQLite. Existing Java-era files remain readable; see [migration notes](docs/PYTHON_MIGRATION.md).

On Android, these writable files live in app-private storage and the catalogs and images remain read-only APK assets.

The default user data directory is `~/.cooking-planner` on Linux and `%USERPROFILE%\.cooking-planner` on Windows. Set `COOKING_PLANNER_DATA_DIR` to move it. Set `COOKING_PLANNER_CATALOG_DIR` for a different source catalog directory. Settings live in `<data directory>/client.cfg` (see [example](src/frontend/client.cfg.example)). Close the app before backing up all five user files.

`client.cfg` accepts `[ui] scale`, `locale`, `window_width`, `window_height`, and `fullscreen`. Language, scale, and fullscreen controls save their choices there. Missing, invalid, or out-of-range values use built-in defaults; window size is limited to 900–3840 by 650–2160. Desktop window settings are ignored on Android. Older `[backend]` settings are ignored. The app does not automatically load a `.env` file.

Each supplied recipe has a local image. Image maintenance is separate from the everyday Makefile: run `python3 scripts/images/import_local_recipe_images.py` to import replacements and `python3 scripts/images/verify_recipe_images.py` to check references and credits. See [recipe images](docs/RECIPE_IMAGES.md). All 586 existing image rights remain pending and must be reviewed before publication.

## Architecture and checks

The frontend calls `LocalPlanner`, which owns the recipe, ingredient, plan, and storage services. Startup loads overview counts and plans first, then loads the recipe catalog and prices. Feature views are built when opened, and the frontend caches only the active language's catalog. User data remains in the configured local directory; the app opens no HTTP listener. See [architecture](docs/ARCHITECTURE.md), [code quality](docs/CODE_QUALITY.md), and [security audit](docs/SECURITY_AUDIT.md).

`make quality` requires Kivy and a display for desktop coverage. It runs separate frontend/backend coverage floors. The source app's Kivy event loop should be checked at 100% and 200% scale with every main tab open after UI changes. The Android build and device checks use their own workflow; the desktop commands do not produce an APK or iOS app.
