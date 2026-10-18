# Architecture

```text
Kivy views -> LocalPlanner -> Python feature stores
                                 |             |
                          catalog JSON       plans.json + SQLite
                          + edit overlay     + shopping.json
```

The frontend and backend are separate Python packages under `src/frontend` and `src/backend`. The launcher creates one `LocalPlanner` and passes it to the Kivy app. It calls the recipe, ingredient, and plan stores in process; no socket or HTTP server starts. Data work and queued shopping writes stay on worker threads, with UI updates scheduled on the Kivy event loop. The launcher closes SQLite storage after outstanding worker tasks finish. Startup shows the overview from small catalog counts and current plans before loading the full recipe catalog and prices. Feature views are built on demand and inactive panels are released; the frontend keeps only the active locale's recipe catalog, reuses it across week changes, and invalidates it after admin edits. The app coalesces rapid refresh requests to the latest state. The browser builds its searchable text once per view. Shopping rows render in frame-sized batches, and recipe images load asynchronously.

## Feature ownership

| Package | Responsibility |
| --- | --- |
| `cooking_planner.recipes`, `.plans`, `.shopping` | Kivy feature views and shopping draft |
| `cooking_planner.AppShell` | Main shell and feature tab construction |
| `cooking_planner.shopping.persistence` | Shopping draft validation, recovery copies, and atomic JSON writes |
| `cooking_planner_backend.core` | Local planner lifecycle, shared conflict and ID validation |
| `cooking_planner_backend.stores.RecipeStore` and `recipe_mapper` | Catalog behavior, admin overlays, and recipe DTO mapping |
| `cooking_planner_backend.stores.IngredientStore` | Ingredient translations, search, prices |
| `cooking_planner_backend.stores.PlanStore` | Meal-plan persistence and localized titles |
| `cooking_planner_backend.entities` | One SQLAlchemy model per file |
| `cooking_planner_backend.repositories` | SQLite sessions and atomic JSON file operations |

## Storage and compatibility

Catalogs use `data/recipes_<language>.json` and are never written by the app. They are validated for version, language, count, IDs, and required recipe content before ingredient seeding. Recipes retain stable IDs across translations and plans. Admin changes use `recipe-edits.json` version 1, the same overlay shape as the earlier backend. Recipe edits require ingredient IDs already present in SQLite and use SQLite translations for their saved names. New recipe IDs include the selected country code when present, which distinguishes recipes with the same dish name and different origins. The image picker passes selected photo bytes to `RecipeImageStore`; it validates type, size, recipe-specific reference, and content duplicates before writing them under the configured user data directory's `recipe_images/<recipe-id>/` folder. The bundled image catalog stays read only. A short-lived `recipe-edits.pending.json` records the before and after overlay around a SQLAlchemy marker transaction. On restart, that marker chooses which overlay to keep after an interrupted edit.

`plans.json` keeps date, meal slot, recipe ID, servings, and stable random positive plan ID. Missing or deleted recipes remain on the plan with a “Missing recipe” title and no derived shopping ingredients. Shopping offers plans dated today onward, independent of the displayed week, but projects ingredients only from explicitly selected plan IDs. Its `shopping.json` entry `upcoming` keeps selected plan IDs, ingredient choices, custom items, checked purchases, and `boughtPlans` signatures. An older automatic `upcoming` entry is converted once to a snapshot of its currently visible selections, so later Week additions require import. A recipe is bought only while all its ingredients are checked and its recipe and servings match the saved signature. Initial use carries the current week's existing shopping choices forward. Clearing Shopping leaves the Week plan intact. Older week entries remain readable. The `pending` list records idempotent ingredient and price writes before calling the backend. Successful writes are removed from the list; interrupted writes replay on the next app launch.

SQLAlchemy uses the existing `cooking-planner.db` tables: `ingredient`, `ingredient_translation`, `ingredient_price`, and `migration_marker`. Prices remain integer cents. A positive `basis_quantity` and `week_start='*'` denote a reusable reference price; older week prices retain a null basis. A missing basis column is added without replacing existing rows. Existing `shopping.json` prices are imported once without changing that file. Saved ingredient names are not overwritten by catalog seeding. Catalog seeding reads existing ingredient IDs and translations in bulk rather than querying each ingredient separately.

These SQLite tables are in third normal form. Ingredient identity is stored once in `ingredient`; localized names depend on `(ingredient_id, locale)` in `ingredient_translation`; amounts and optional basis quantities depend on `(ingredient_id, week_start, unit)` in `ingredient_price`. Unique constraints enforce those keys and foreign keys link dependent rows to `ingredient`. `migration_marker` stores one key per completed migration. Shopping's bought status belongs to `shopping.json`, so no SQLite schema migration is needed. Plan labels use raw localized recipe names instead of constructing every recipe DTO and reading ingredient translations.

Settings remain in `client.cfg`, and all writable files remain under `COOKING_PLANNER_DATA_DIR` or the platform default. Close the app before copying them for backup.

## Local service and mobile direction

`LocalPlanner` exposes recipe, admin, plan, ingredient, and price operations to the Kivy app. Validation and persistence remain in feature stores and repositories. The Android entry point uses the same frontend and backend packages, stages the catalogs and images as read-only APK assets, and writes plans, settings, and SQLite data to app-private storage. Buildozer and python-for-android supply the Android dependency recipes. Device compatibility still requires APK installation and runtime checks; iOS remains unbuilt.

The desktop distribution workflow builds a Python wheel and PyInstaller executable. Before freezing, it stages compact JPEG catalog images and rewrites references in copies of both locale catalogs and the attribution CSV. Linux wraps that executable in an AppImage; Windows wraps it in an Inno Setup installer. Android builds a separate Kivy APK through Buildozer. The user data directory is outside the bundled files on every platform.
