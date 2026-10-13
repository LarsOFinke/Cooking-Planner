# Architecture

```text
Kivy views -> ApiClient -> loopback FastAPI routes -> Python feature stores
                                               |             |
                                        catalog JSON       plans.json + SQLite
                                        + edit overlay     + shopping.json
```

The frontend and backend are separate Python packages under `src/frontend` and `src/backend`. Kivy views depend on `ApiClient`, which preserves the existing HTTP contract. `api/backend.py` starts Uvicorn in an app-owned thread and stops it on exit. The server binds only to `127.0.0.1`; a per-launch token prevents a different process on the same port from being mistaken for the app's server. The Kivy main thread never performs the bulk catalog load; app requests use worker threads and schedule UI updates on the Kivy event loop.

## Feature ownership

| Package | Responsibility |
| --- | --- |
| `cooking_planner.recipes`, `.plans`, `.shopping` | Kivy feature views and shopping draft |
| `cooking_planner.api` | HTTP client and local backend lifecycle |
| `cooking_planner_backend.routes` | HTTP controllers grouped by recipe, plan, and ingredient paths |
| `cooking_planner_backend.recipes.service` and `.mapper` | Catalog behavior, admin overlays, and recipe DTO mapping |
| `cooking_planner_backend.ingredients.service` | Ingredient translations, search, prices |
| `cooking_planner_backend.plans.service` | Meal-plan persistence and shopping aggregation |
| `cooking_planner_backend.entities` | One SQLAlchemy model per file |
| `cooking_planner_backend.repositories` | SQLite sessions and atomic JSON file operations |
| `cooking_planner_backend.app` | FastAPI composition and HTTP error mapping |

## Storage and compatibility

Catalogs use `data/recipes_<language>.json` and are never written by the app. They are validated for version, language, count, IDs, and required recipe content before ingredient seeding. Recipes retain stable IDs across translations and plans. Admin changes use `recipe-edits.json` version 1, the same overlay shape as the earlier backend. A short-lived `recipe-edits.pending.json` records the before and after overlay around a SQLAlchemy transaction. On restart, a SQLite commit marker chooses which overlay to keep, so interrupted edits do not leave the file and translated ingredient names at different revisions.

`plans.json` keeps date, meal slot, recipe ID, servings, and stable random positive plan ID. Missing or deleted recipes remain on the plan with a “Missing recipe” title and no derived shopping ingredients. `shopping.json` keeps weekly meal and ingredient choices, custom items, and checked purchases. Its `pending` list records idempotent ingredient and price writes before calling the backend. Successful writes are removed from the list; interrupted writes replay on the next app launch.

SQLAlchemy uses the existing `cooking-planner.db` tables: `ingredient`, `ingredient_translation`, `ingredient_price`, and `migration_marker`. Prices remain integer cents. A positive `basis_quantity` and `week_start='*'` denote a reusable reference price; older week prices retain a null basis. A missing basis column is added without replacing existing rows. Existing `shopping.json` prices are imported once without changing that file. Saved ingredient names are not overwritten by catalog seeding.

Settings remain in `client.cfg`, and all writable files remain under `COOKING_PLANNER_DATA_DIR` or the platform default. Close the app before copying them for backup.

## API and mobile direction

The HTTP endpoints retain the desktop client's recipe, admin, plan, ingredient, and price paths. The backend is hosted inside the same Python process, so packaging no longer needs Java. FastAPI and SQLAlchemy are separate from the Kivy views; an Android or iOS entry point can reuse the backend package. Mobile work still needs platform data-directory wiring, dependency recipes, app lifecycle checks, and device builds. Android and iOS compatibility has not been verified by the desktop checks.

The desktop distribution workflow builds a Python wheel and PyInstaller executable. Linux wraps that executable in an AppImage; Windows wraps it in an Inno Setup installer. The user data directory is outside the bundled files.
