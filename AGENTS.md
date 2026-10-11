# Cooking Planner working guide

Read `README.md`, `docs/ARCHITECTURE.md`, `docs/CODE_QUALITY.md`, and `docs/SPRING_CLEANUP.md` before changing behavior. Keep recipes and plans in feature-owned backend packages. The desktop imports only its HTTP client, never backend Java classes. Recipe catalogs use `data/recipes_<language>.json` and are read only; preserve every catalog and existing meal plan on failures or upgrades. Keep writable plans and client settings under the configured user data directory.

Run `make quality` for syntax, Ruff, tests, and JaCoCo's 60% backend line coverage floor. For desktop changes, also run a real Kivy event-loop smoke on a machine with a display; check normal and 200% UI scaling before calling the UI verified. `make dev` builds the backend JAR and opens the desktop. `make linux` and `scripts/build/build-windows.ps1` own the native packaging workflow; do not claim either build verified without running it on that platform.

Do not add empty layers simply to match a package checklist. Add a mapper when an external recipe format actually differs from the internal recipe DTO; add utilities only for code shared by multiple features.
