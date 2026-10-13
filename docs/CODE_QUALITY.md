# Code quality and tests

Run `make quality` from the repository root. It checks Python syntax, one PascalCase file per production class, Ruff, whitespace, frontend and backend tests, and separate 60% source-line coverage floors. The coverage run requires Kivy and a display. `QUALITY_PYTHON` selects another Python environment with the packages from `src/requirements.txt` and `src/requirements-dev.txt` installed.

Backend tests cover the real HTTP contract, catalog localization, plan and shopping persistence, admin overlays, ingredient names, prices, Java-era SQLite schema upgrades, legacy shopping-price import, and interrupted recipe-edit recovery. Frontend tests cover navigation, filters, scaling, planning controls, shopping drafts, background write durability, admin forms, API client serialization, and backend startup. Tests that write user data use temporary directories; bundled catalogs remain read only.

For desktop changes, run a real Kivy event-loop smoke at 100% and 200% scale on a display. A passing widget suite does not replace visual review of the packaged app. Build Linux and Windows distributables on their respective platforms and verify startup, language switching, plan persistence, shopping totals, scaling, and Exit before calling a release verified.

For Android, run `make compile-android` on a provisioned Linux build machine, then install the debug APK on an arm64 device or emulator. Verify startup, language switching, catalog images, plan and shopping persistence across restarts, and pause/resume. A desktop smoke does not verify the Android event loop or dependency recipes.

`loc-rank --top 20 src` guides cleanup by physical line count. The largest production UI classes were split by responsibility: app shell, admin form pages, recipe filters, shopping rendering, shopping persistence, and admin API actions. Production files defining classes use the class's PascalCase name. Test modules retain `test_*.py` names for discovery. The long `test_ui_flow.py` remains one integration suite because its scenarios share a real Kivy fixture. See [spring cleanup](SPRING_CLEANUP.md) for the current audit.
