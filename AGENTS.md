# Cooking Planner working guide

Read `README.md` and `docs/ARCHITECTURE.md` before changing behavior. Keep recipes and plans in feature-owned backend packages. The desktop imports only its HTTP client, never backend Java classes. Recipe catalogs use `recipes_<language>.json`; preserve every catalog and existing meal plans on failures or upgrades. Keep all user data under the configured data directory.

For backend changes, run `mvn -f backend/pom.xml test`. For desktop changes, run Python syntax checks and a real Kivy event-loop smoke on a machine with a display; check normal and 200% UI scaling before calling the UI verified. Build the backend JAR before running the desktop. Do not claim Windows or iOS packaging without a build on those platforms.

Do not add empty layers simply to match a package checklist. Add a mapper when an external recipe format actually differs from the internal recipe DTO; add utilities only for code shared by multiple features.
