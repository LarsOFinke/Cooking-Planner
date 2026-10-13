# Cooking Planner

Cooking Planner is a local Windows/Linux desktop app for browsing English and German recipes, planning meals, estimating costs, and preparing a shopping list. The Kivy frontend talks over loopback HTTP to a separate Python FastAPI backend. SQLAlchemy stores ingredient names and prices in SQLite. The backend runs in a thread owned by the app, so there is no separate runtime or service to install.

The source tree keeps the UI in `src/frontend/cooking_planner`, API and data logic in `src/backend/cooking_planner_backend`, and tests in `src/tests`. Build scripts live in `scripts/build/linux`, `scripts/build/windows`, and `scripts/build/common`; development, quality, image, and install scripts have their own directories.

## Run and build

Install Python 3.11–3.14, then use these commands from the repository root:

| Purpose | Command | Result |
| --- | --- | --- |
| Source run | `make dev` | Installs missing Python packages and opens the app |
| Tests | `make test` | Runs frontend and backend Python tests |
| Full checks | `make quality` | Syntax, Ruff, tests, and separate 60% coverage floors |
| Linux distribution | `make compile-linux` | `dist/linux/CookingPlanner-<arch>.AppImage` |
| Windows distribution | `make compile-windows` on Windows | `dist/windows/CookingPlanner-Setup.exe` |

`make linux` and `make windows` are aliases retained for existing scripts. `make help` lists the main commands. On Windows without GNU Make, use `scripts/development/dev-windows.ps1` or `scripts/build/windows/build-windows.ps1` directly. The first source run needs network access to install Python packages. Set `PYTHON_BIN` to choose a supported interpreter or `DEV_PYTHON` to use an existing environment.

The distribution builds bundle Python, Kivy, the backend, and the recipe catalogs. Users need no Python installation. Build each installer on its target operating system. The Linux AppImage runs directly after `chmod +x`; it can be copied to `~/.local/bin/cooking-planner` for a terminal command. The Windows installer installs to the current user's Programs directory and creates a Start menu shortcut. `scripts/install/` contains optional build-and-install shortcuts for the build machine.

The Linux builder uses the official checksum-verified `appimagetool` 1.9.1 release, or a tool supplied through `APPIMAGETOOL`. The Windows builder uses Inno Setup 6 and can obtain it through WinGet. Builds retain logs in `build/logs/`. The AppImage and Windows installer need target-system runtime checks before release. Desktop parity is the scope of this refactor; Android APK and iOS packaging are later phases.

## Features and data

The Explore view has filters, recipe details, cooking steps, and a local image gallery. Week stores meals by day and slot with servings. Shopping derives ingredients from plans and lets you include meals or ingredients, add custom items, check purchases, and save prices. Admin edits recipes and ingredient translations across the available languages. Reference prices per quantity drive recipe and weekly cost estimates. The scale menu saves 100–200% UI scaling in `client.cfg`.

Bundled catalogs are `data/recipes_<language>.json`. The supplied English and German catalogs each have 586 recipes with shared IDs. They are read only. Recipe additions, edits, omissions, and deletion markers go to `recipe-edits.json` in the user data directory. Meal plans go to `plans.json`; ingredient names and prices go to `cooking-planner.db`; shopping choices and custom items go to `shopping.json`. The shopping file also queues unfinished SQLite writes for retry after interruption. Recipe edits use a recovery journal while their SQLite translations and JSON overlay are committed. Existing Java-era files remain readable; see [migration notes](docs/PYTHON_MIGRATION.md).

The default user data directory is `~/.cooking-planner` on Linux and `%USERPROFILE%\.cooking-planner` on Windows. Set `COOKING_PLANNER_DATA_DIR` to move it. Set `COOKING_PLANNER_CATALOG_DIR` for a different source catalog directory. The backend port comes from `COOKING_PLANNER_PORT` or `<data directory>/client.cfg` (see [example](src/frontend/client.cfg.example)). Close the app before backing up all five user files.

Each supplied recipe has a local image. Image maintenance is separate from the everyday Makefile: run `python3 scripts/images/import_local_recipe_images.py` to import replacements and `python3 scripts/images/verify_recipe_images.py` to check references and credits. See [recipe images](docs/RECIPE_IMAGES.md). All 586 existing image rights remain pending and must be reviewed before publication.

## Architecture and checks

The frontend imports only its HTTP client and backend launcher. The backend package owns recipe, ingredient, plan, and storage behavior. FastAPI binds to `127.0.0.1`; admin endpoints have no account system, so the service must stay local. See [architecture](docs/ARCHITECTURE.md) and [code quality](docs/CODE_QUALITY.md).

`make quality` requires Kivy and a display for desktop coverage. It currently passes 73 tests and separate frontend/backend coverage floors. The source app's Kivy event loop was checked at 100% and 200% scale with every main tab open. Android and iOS need their own packaging and runtime validation; no APK or iOS app is produced by the desktop commands.
