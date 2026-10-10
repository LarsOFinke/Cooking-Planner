# Architecture and next decisions

```text
Kivy desktop -> ApiClient -> loopback HTTP controllers -> services -> JSON repositories
                     Spring Boot process              -> JsonFileStore
```

`recipes` and `plans` own their DTOs, entities, controllers, services, and repositories. `shared/JsonFileStore` owns file IO. The Kivy package knows only the HTTP contract; the backend has no Kivy dependency. This follows the toolkit's local desktop profile and borrows Project-Planner's feature ownership and navy/gold visual direction, without copying its larger infrastructure.

## Why JSON for V1

The original SQLite suggestion is reasonable for larger editable catalogs. Here, a local single-user flow with language-specific recipe catalogs and meal slots does not need a database. `recipes_<language>.json` and `plans.json` are separate from `client.cfg` and environment settings. Repositories isolate storage so a SQLite migration can keep the API and UI stable.

Writes create a temporary file in the same directory, then replace one JSON file atomically. There is no cross-file transaction. Recipe deletion is rejected while any plan references it. File contents are never reset on startup; unreadable files cause an error. A future schema change needs an explicit versioned migration before V1 data is relied on long term.

## API V1

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Local process health |
| GET, POST | `/api/recipes` | List or create recipes |
| GET | `/api/recipes/locales` | List imported language suffixes |
| PUT, DELETE | `/api/recipes/{id}` | Update or remove a recipe |
| POST | `/api/recipes/import?locale=de` | Validate and append 1–500 recipes to a language catalog in one write |
| GET | `/api/plans?from=YYYY-MM-DD&to=YYYY-MM-DD` | Read up to 62 days |
| PUT | `/api/plans` | Assign/replace a date and meal type |
| DELETE | `/api/plans/{id}` | Remove a planned meal |

`PUT /api/plans` accepts `date`, `mealType` (`BREAKFAST`, `LUNCH`, `DINNER`), and `recipeId`.

Recipe list and create endpoints accept `?locale=en` (default), with two-letter language codes. Recipe IDs remain globally unique across catalogs so plans keep referencing the selected language variant. There is no translation mapping without a shared source key. The desktop derives the import locale from `recipes_<language>.json` and sends it to the API.

## Packaging and iOS

Windows and Linux each require a native PyInstaller build; the JAR is portable but Java must be installed. A later installer can bundle a Java runtime. [Kivy documents an iOS packaging path through `kivy-ios` and Xcode](https://kivy.org/doc/stable/guide/packaging-ios.html), but this local Spring Boot process is a desktop design. An iOS version would need a reachable backend or a separate on-device persistence implementation behind the client boundary. iOS compatibility is therefore a later architecture decision, not a property of this V1 desktop bundle.

## Next slice

Once the real recipe JSON is available, confirm its field mapping and whether translations share a stable recipe key; then add duplicate handling and a safe re-import path. Before release, verify live API requests, real Kivy interactions at 100% and 200% scale, Windows packaging, restore from copied data files, and a bundled Java runtime if a standalone executable is required.
