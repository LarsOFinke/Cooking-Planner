# Packaging and shopping checks

Run `make quality` after changes. For desktop UI changes, open the source app at 100% and 200% UI scale on a display. Build the Windows installer only on Windows and inspect the CI artifact before calling the installer verified.

Desktop builds run `scripts/build/common/stage_catalogs.py` after validating source image rights and references. The script writes compact JPEG copies and rewritten English and German catalog references to `build/catalogs`; source PNGs, catalog JSON, and attribution records stay intact. It requires Pillow from `src/requirements-build.txt`. The desktop package includes the staged catalogs. Check both locale references, the attribution CSV, Kivy image loading, and the installed package's `--verify-package` result when changing this path.

Shopping now uses all plans dated today or later, independent of the open Week page. The `upcoming` entry in `shopping.json` stores shopping choices and `boughtPlans` signatures. Initial use copies the current week's manual items and checks. A recipe is marked bought only after all its ingredient rows are checked; changing a recipe or its servings invalidates the saved signature. Shared ingredients count toward each recipe. Past plans remain in `plans.json` and are never deleted by Shopping.

The SQLite ingredient tables already meet third normal form: `ingredient` owns IDs, `ingredient_translation` owns names by ingredient and locale, and `ingredient_price` owns amounts by ingredient, period and unit. No schema migration is needed for the shopping change; shopping state remains in its existing JSON file. `PlanStore` now reads raw localized recipe names when labeling plans, avoiding full recipe DTO construction and ingredient translation queries.
