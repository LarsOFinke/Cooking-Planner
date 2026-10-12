# Cooking Planner

A local Windows/Linux desktop prototype for exploring a multilingual recipe catalog, planning meals, and preparing a shopping list. Kivy provides the desktop interface; a Spring Boot process serves the catalog and plan over loopback HTTP. SQLite stores normalized ingredient names and shopping prices in the configured user data directory.

## Run for development

Install Java 21, Maven, and Python 3.11–3.14, then run from the repository root:

```bash
make dev
```

On Windows, `make dev` works with GNU Make, or run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/development/dev-windows.ps1`. Development scripts create a local virtual environment, install Kivy, build the backend JAR, and open the app. They select your default Python 3.14 when available. Python 3.14 uses the Kivy 3 development wheel from Kivy's nightly index; Python 3.11–3.13 use stable Kivy 2.3.1. An internet connection is needed for the first installation. `PYTHON_BIN` selects another interpreter, `DEV_PYTHON` selects an already provisioned interpreter with compatible Kivy, and `MAVEN_REPO` selects a writable Maven cache. The launcher starts and stops the local backend automatically.

`make dev` skips Maven tests for a faster launch; use `make quality` to run them. On Linux, normal copy and paste work through Kivy's SDL clipboard. Install `xclip` or `xsel` only if you need X11 primary-selection cutbuffer support. A `/dev/input/event*` permission warning concerns Kivy's optional touch-device probe; mouse and keyboard input use SDL3. Kivy's first-run configuration upgrade is saved automatically.

The language menu switches between `data/recipes_en.json` and `data/recipes_de.json` using their suffix. The supplied files contain 586 recipes each, with shared recipe IDs. Overview introduces the modules and shows catalog and weekly counts. Explore has separate overview, ingredient, and recipe detail pages, with labeled filters in a scrollable popup. The Week planner stores meals and servings; the Shopping list derives its ingredients from those plans, includes newly planned meals automatically, and lets you select several meals, search saved ingredients for new items, choose units, add custom items, remove ingredients, check items off, and copy the remainder. **Exit** is at the bottom-left, and **Recipe admin** is at the bottom-right. The scale menu offers 100–200% and saves the choice in `client.cfg`; horizontal and vertical scrolling keep the interface usable at larger scales. The Fullscreen button switches between full-screen and windowed mode and updates its label.

The **Recipe admin** panel adds, edits, and deletes recipes through labeled fields. Its Ingredients page can search saved ingredients and fill their shared ID and available English/German names. The separate **Ingredient catalog** view creates ingredients, edits localized names, and deletes entries that are not used by a recipe, shopping item, or saved price. Its Recipe page edits each cooking step separately, including the ingredient IDs used by that step and localized text. The Status overview page shows the latest app status. Shared codes, quantities, times, image references, step order, and step ingredient IDs update every included language; recipe names, ingredient names, and step text are edited per language. Adding a recipe requires a translation or an explicit **Omit intentionally** choice for every language. **Reset to loaded** discards unsaved form changes. An omitted recipe does not appear in that language's catalog.

Shopping items can have an optional euro price for the full quantity shown on the row. The list shows the sum of entered prices and how many items have prices; blank prices are excluded. Prices are included when copying priced items and are saved per week in `cooking-planner.db`. Existing prices in `shopping.json` are imported once without modifying that file.
The Week planner gives each day one full-width row with evenly sized meal fields. When shopping ingredients have prices, it shows optional day and week estimates. A shared ingredient price is divided among the selected planned meals according to their ingredient quantities and servings; coverage counts show when the estimate is partial.

Place local recipe pictures under `data/recipe_images/<recipe-id>/image_01.webp` (or `.png`/`.jpg`) and run `make images-sync`; up to three numbered pictures per recipe are supported. `make images` also searches Wikimedia Commons, while `make images-verify` checks both locale references, files, and credits. See [Recipe images](docs/RECIPE_IMAGES.md). Local pictures with unknown rights are visibly marked pending until credits are supplied.
Click a recipe picture in Explore to open the full-window gallery with previous/next controls and thumbnails.

Recipe catalog files use a top-level `metadata` object and `recipes` array. The backend reads them from `data/` without modifying them. To add a locale, provide a `recipes_<two-letter-language>.json` file with the same schema and stable IDs. `metadata.language` must match the suffix. Schema 1.2 catalogs also provide localized `instructions.steps`; Explore shows every step in the Recipe tab. Ingredient IDs and localized names are imported into SQLite and used by ingredient search. The app shows the dataset notes in **About this catalog**.

Recipe admin changes are saved atomically as `recipe-edits.json` in the configured user data directory. Bundled catalogs remain read only, so edits survive catalog upgrades. Include this file when backing up user data.

Meal plans are saved to `~/.cooking-planner/plans.json` on Linux or `%USERPROFILE%\.cooking-planner\plans.json` on Windows. Ingredient names and shopping prices are stored in `cooking-planner.db`; other shopping draft state remains in `shopping.json`. Set `COOKING_PLANNER_DATA_DIR` to move this directory. Set `COOKING_PLANNER_CATALOG_DIR` to use a different recipe catalog directory for a source run. The backend port comes from `COOKING_PLANNER_PORT` or `<data directory>/client.cfg` (see [example](desktop/client.cfg.example)). Close the app before backing up these files.

## Build

| Target | Command | Output |
| --- | --- | --- |
| Python wheel | `make wheel` | `dist/wheels/` |
| Linux single file | `make linux` | `dist/linux/CookingPlanner` |
| Windows single file | `make windows` on Windows | `dist/windows/CookingPlanner.exe` |

The Windows build can also be started with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build/build-windows.ps1`. Each platform build bundles the Python frontend, Spring Boot JAR, a trimmed Java runtime, and the catalog files. The one-file executable extracts bundled files to a temporary directory at startup. Build the Windows executable on Windows and the Linux executable on Linux. End users do not need a separate Python or Java installation. The build machine needs Python 3.14 by default, Java 21 with `jlink`, Maven, and access to Python packages. Linux builds can use `PYTHON_BIN` to select Python 3.11–3.13 if needed.

## Checks and scope

`scripts/development/` contains local setup and launch scripts, `scripts/build/` contains packaging entry points, `scripts/quality/` contains checks, and `scripts/images/` contains recipe image tools. The root `Makefile` provides the usual commands for each group.

Run `make test` for tests and JaCoCo's 60% backend line coverage gate, or `make quality` for syntax, Ruff, whitespace, and both 60% coverage gates. Desktop line coverage is currently 83.4%; see [code quality](docs/CODE_QUALITY.md) and the [Spring cleanup list](docs/SPRING_CLEANUP.md). Kivy 3 widget tests and event-loop checks at 100% and 200% scale passed on Python 3.14 with a desktop display; visual release review is still needed. Native distributables also need target-platform verification. Python 3.14's default build still has the GIL; the desktop uses worker threads for HTTP and schedules UI changes on Kivy's main thread. The backend binds to `127.0.0.1` for this local single-user prototype. See [architecture](docs/ARCHITECTURE.md) for module boundaries and the iOS consideration.
