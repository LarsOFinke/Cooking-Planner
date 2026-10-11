# Spring Boot cleanup

This document records the backend state after the JSON catalog migration and the work required before distributing V1.

## Current state

- The API reads `data/recipes_<locale>.json` as versioned, read-only catalogs. Shared recipe IDs connect translations and meal plans.
- The backend writes `plans.json` and `recipe-edits.json` atomically through `JsonFileStore`. The supplied recipe catalogs remain read only. The desktop separately stores the user-controlled weekly shopping draft in `shopping.json`.
- Controllers contain HTTP and validation concerns; services own planning and shopping behavior; repositories own JSON access; `CatalogMapper` translates the external catalog schema.
- The process binds to loopback. The desktop launcher starts it and stops only the process it owns.
- `mvn verify` runs tests and the JaCoCo line coverage gate. The current backend report is at `backend/target/site/jacoco/index.html`.

## Before a first distributed build

1. Run `make quality` and inspect any coverage drop. Keep real catalog fixtures read only in tests and put writable plan data in temporary directories.
2. Verify Linux and Windows single-file builds on the target systems, including startup, language switching, plan persistence, shopping totals, scaling, and Exit.
3. Verify a backup and restore of `plans.json` and `recipe-edits.json` with the application closed. Keep the bundled catalog files outside the writable data directory.
4. Decide whether catalog validation should scan every locale at startup or continue validating on first use. The current lazy validation avoids extra startup work but reveals a bad locale only when selected.
5. Add a versioned migration if the `plans.json` or `recipe-edits.json` structure changes. Do not silently overwrite an older user file.
6. Review dependency updates and the local-only security boundary before exposing any endpoint beyond `127.0.0.1`.

The recipe admin endpoint stores user edits as an overlay and leaves bundled catalogs unchanged. No SQLite migration is planned for V1.
