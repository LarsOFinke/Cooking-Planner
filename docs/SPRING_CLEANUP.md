# Spring Boot cleanup

This document records the backend state after the JSON catalog migration and the work required before distributing V1.

## Current state

- The API reads `data/recipes_<locale>.json` as versioned, read-only catalogs. Shared recipe IDs connect translations and meal plans; schema 1.2 includes localized instruction steps.
- The backend writes `plans.json` and `recipe-edits.json` atomically through `JsonFileStore`. It stores normalized ingredient identities, localized names, and weekly prices in SQLite through JPA repositories. The supplied recipe catalogs remain read only. The desktop separately stores the other weekly shopping state in `shopping.json`.
- Controllers contain HTTP and validation concerns; services own planning and shopping behavior; repositories own JSON access; `CatalogMapper` translates the external catalog schema.
- The process binds to loopback. The desktop launcher starts it and stops only the process it owns.
- `mvn verify` runs tests and the JaCoCo line coverage gate. The current backend report is at `backend/target/site/jacoco/index.html`.

## Before a first distributed build

1. Run `make quality` and inspect any coverage drop. Keep real catalog fixtures read only in tests and put writable plan data in temporary directories.
2. Verify Linux and Windows single-file builds on the target systems, including startup, language switching, plan persistence, shopping totals, scaling, and Exit.
3. Verify a backup and restore of `plans.json`, `recipe-edits.json`, `shopping.json`, and `cooking-planner.db` with the application closed. Keep the bundled catalog files outside the writable data directory.
4. Catalog validation scans every available locale during ingredient seeding at startup. Keep this behavior so a bad catalog fails before the app accepts requests; revisit the startup cost only if catalog growth warrants it.
5. Add a versioned migration if the `plans.json` or `recipe-edits.json` structure changes. Do not silently overwrite an older user file.
6. Review dependency updates and the local-only security boundary before exposing any endpoint beyond `127.0.0.1`.

The recipe admin endpoint stores user edits as an overlay and leaves bundled catalogs unchanged. SQLite stores ingredient identity, localized names, and prices; existing shopping prices are imported from `shopping.json` once.

## Cleanup check on 2026-10-12

- `make quality` passed: 13 backend tests, the JaCoCo gate (93.5% backend line coverage), and 84.3% desktop line coverage. All 48 desktop tests also passed using the Kivy development environment with a display.
- A closed-app backup and restore into a fresh temporary data directory recovered a saved plan, recipe edit, shopping draft item, and SQLite price. Bundled catalogs stayed outside both data directories.
- `make linux` built `dist/linux/CookingPlanner` after correcting the PyInstaller asset paths. The packaged app and bundled backend launched on the local display at 100% and 200% scale with temporary user data, and both bundled catalog languages loaded. A separate real Kivy event-loop check confirmed hover behavior across Overview, Explore, Week, and Shopping at both scales. Visual review, the packaged navigation and Exit workflow, and the Windows build and runtime checks remain open.
- Catalogs are validated across available locales at startup before ingredient seeding. The backend remains bound to `127.0.0.1`; the admin endpoints have no authentication, so the service must remain local only. No plan or edit file format changed in this cleanup.
- Dependency review found Spring Boot and JaCoCo on their current release lines. SQLite JDBC remains at the version managed by Spring Boot; evaluate newer driver patches with the full quality and backup/restore checks before changing that override.

## Planning dialog follow-up on 2026-10-12

- The planning popup's fixed-height form placed its date controls outside the popup at 200% scale. The form now scrolls while Save and Cancel stay visible. A Kivy event-loop check confirmed both date arrows remain inside the popup at 100% and 200%, and the selected date reaches Save.
- Text input labels were hidden by the rounded control fill. Text inputs use their native background again so dates and other entered values remain readable. Confirmation dialogs now have enough height for their actions at 200%.
- `make quality` passed with 57 desktop tests, 86.7% desktop line coverage, and the backend JaCoCo gate. `make images-verify` passed for all 586 catalog recipes. `make linux` built the single-file executable, and its bundled GUI and API started with both catalogs at 100% and 200% using temporary user data. Windows build and runtime verification remain open.

## Backend maintenance on 2026-10-12

- Price endpoints now reject malformed dates, ingredient IDs, and units with HTTP 400 before writing rows. This keeps the `ingredientId:unit` price key unambiguous while accepting the shopping UI's units.
- Shopping aggregation loads ingredient translations once per request and reuses each planned recipe across meals. The HTTP test checks localized names, summed quantities, and recipe counts for repeated plans.
- Recipe admin saves join ingredient updates to a database transaction, so a failed edit-file write rolls back those updates. The edit file remains the persisted recipe source; SQLite remains the ingredient-name source.
