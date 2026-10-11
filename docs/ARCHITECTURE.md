# Architecture

```text
Kivy views -> ApiClient -> Spring Boot controllers -> services -> repositories
                                                    |               |
                                      catalog JSON + edits     plans.json
                                        (base read only)        (writable)
```

The feature modules own their controllers, entities, mappers, services, and repositories. The desktop views know the HTTP contract and have no direct dependency on Java or catalog file parsing. Recipe IDs are stable strings shared by the locale catalogs. A language switch refreshes recipe names and planned meal titles while preserving selections by ID.

## Desktop packages

`desktop/cooking_planner` keeps the Kivy application and startup launcher at its root. The remaining modules are grouped by the work they own:

| Package | Responsibility |
| --- | --- |
| `api` | HTTP client and lifecycle of the local Spring process |
| `recipes` | Browsing, recipe admin, recipe dialogs, locale filenames, and local images |
| `plans` | Week view and meal planning dialog |
| `shopping` | Persisted weekly draft and shopping view |
| `overview` | Overview tab |
| `ui` | Shared Kivy controls, confirmation dialog, and translations |

`paths.py` resolves catalog and bundled file locations for the launcher and recipe images. Feature views receive data and callbacks from `app.py`; only `api/client.py` calls the backend. Both source and frozen entry points call `launcher.py`, which configures Kivy before loading the app. The wheel discovers every `cooking_planner` subpackage.

## Storage

The catalog repository discovers `recipes_<language>.json` in `data/` (or `COOKING_PLANNER_CATALOG_DIR`). It validates the `1.1.0` metadata schema, language suffix, recipe count, and unique IDs, then caches each file until its modification time or the edit revision changes. Base catalogs are never written by the admin API. Additions, translations, intentional omissions, and deletion markers are stored together in the atomically replaced `recipe-edits.json` under the user data directory. Shared fields are copied from the edit's source language to every included translation. Recipe IDs remain stable, so existing meal plans are preserved when a recipe is deleted, although its title becomes "Missing recipe" and it contributes no shopping ingredients. Deleted IDs cannot be reused. The plan repository stores date, meal slot, recipe ID, and servings in `plans.json` under the same user data directory. Settings such as the UI scale and port live in `client.cfg` and environment variables.

The shopping service multiplies per-person ingredient amounts by planned servings and groups by ingredient ID and unit. The desktop shopping draft derives its meal ingredients from the current backend plans, with optional meal exclusions, custom items, removed ingredients, checked purchases, and euro prices for the displayed quantities per week. Prices are keyed by ingredient ID and unit, so they survive plan refreshes while the item remains in the list. It persists in `shopping.json` beside `client.cfg`; older explicit meal selections are migrated when loaded. Amounts and times are catalog estimates. No nutrition, allergen certification, recipe instructions, accounts, or cloud sync are included.
The Week planner allocates each priced shopping ingredient to selected planned meals in proportion to ingredient quantity and servings. It shows partial day and week cost estimates with priced ingredient coverage; unpriced or removed ingredients and meals excluded from the shopping draft have no allocated cost. Custom shopping items are not assigned to meals.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Process health |
| GET | `/api/recipes/locales` | Available filename suffixes |
| GET | `/api/recipes?locale=en` | Localized catalog |
| GET | `/api/recipes/info?locale=en` | Catalog notes and counts |
| GET | `/api/recipes/{id}?locale=en` | One localized recipe |
| GET | `/api/admin/recipes` | IDs and available translated names |
| GET | `/api/admin/recipes/{id}` | Raw JSON for each language, with `null` for omissions |
| POST | `/api/admin/recipes/{id}` | Add a recipe and choose each language |
| PUT | `/api/admin/recipes/{id}` | Edit a recipe across languages |
| DELETE | `/api/admin/recipes/{id}` | Hide a recipe in every language |
| GET | `/api/plans?from=YYYY-MM-DD&to=YYYY-MM-DD&locale=en` | Localized weekly plans |
| PUT | `/api/plans` | Assign a recipe and servings to a day and meal slot |
| DELETE | `/api/plans/{id}` | Remove a planned meal |
| GET | `/api/plans/shopping?from=YYYY-MM-DD&to=YYYY-MM-DD&locale=en` | Aggregated ingredients |

`PUT /api/plans` accepts `date`, `mealType` (`BREAKFAST`, `LUNCH`, `DINNER`), `recipeId`, and `servings` (1–20). The API is bound to loopback for the desktop app.

Admin POST and PUT accept `sourceLocale` and a `translations` object with one entry per available language. Each entry is a raw recipe object or `null` for an intentional omission. Names and ingredient names are translated per language; IDs, codes, amounts, units, timing, and image references follow the source locale. The admin API uses the same loopback-only, single-user boundary as the rest of the app; it has no separate account system.

## Packaging and iOS

The platform scripts build a Python wheel, Spring Boot JAR, and `jlink` runtime, then package them with PyInstaller and the catalog data. Python executables are platform-specific, so Windows and Linux require separate native builds. The files extract at launch; `plans.json`, `recipe-edits.json`, `shopping.json`, and `client.cfg` live in the user data directory.

Kivy has an iOS packaging route through `kivy-ios`, but a bundled local Java process is a desktop design. An iOS version would require a reachable backend or an on-device plan store behind the client interface. This V1 bundle is for Windows and Linux.
