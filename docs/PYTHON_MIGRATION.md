# Python backend migration

The Java/Spring backend was replaced with `cooking_planner_backend`, a Python package that uses SQLAlchemy. Kivy now calls `LocalPlanner` directly; no loopback server, port, token, or HTTP transport is required. Source runs and desktop distributions need no Java or Maven.

The migration keeps the existing user data directory and file names. `plans.json`, `recipe-edits.json`, and `shopping.json` retain their versioned formats. SQLAlchemy maps the existing SQLite tables and adds `ingredient_price.basis_quantity` only if an older database lacks it. The one-time shopping-price import still reads, but never modifies, `shopping.json`. Read-only catalog files are never rewritten by the app.

Recipe edits use `recipe-edits.pending.json` during a cross-store save. A marker committed in SQLite determines whether startup restores the before or after overlay. Recipe saves reference existing SQLite ingredient IDs and names; ingredient translations are changed through the ingredient catalog. Shopping writes queue idempotent backend actions in `shopping.json` so an interrupted price or custom-item save can resume on launch. Back up the app with the frontend closed, including any pending file if present.

The Linux AppImage build runs on Linux; the Windows installer still needs a Windows build and runtime check. An Android debug APK workflow is now available through `make compile-android`, but its toolchain and device runtime still need verification. iOS packaging remains follow-up work. Mobile builds must validate SQLAlchemy and Kivy on the target toolchains.
