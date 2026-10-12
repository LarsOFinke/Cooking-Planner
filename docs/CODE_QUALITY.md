# Code quality and tests

Run `make quality` from the repository root. It checks Python syntax, Ruff rules, whitespace, Java tests, JaCoCo's 60% backend line coverage floor, and a separate 60% desktop line coverage floor. Ruff can be installed from `desktop/requirements-dev.txt`; use `QUALITY_PYTHON` if it is in a non-default environment. The desktop coverage run requires Kivy and a display. `MAVEN_REPO` selects a custom Maven cache.

The backend passes JaCoCo's 60% line coverage gate; the generated HTML report is `backend/target/site/jacoco/index.html`. The desktop source-line coverage is **87.1% (2841/3261 lines)**, measured by `scripts/quality/python-coverage.py` with Kivy 3 on Python 3.14. The script includes every desktop subpackage. The two gates are independent. Desktop tests cover navigation and filters, scale persistence, planning dialog date selection, daily recipe cost estimates, shopping draft persistence and aggregation, ingredient and recipe admin editing, HTTP client serialization and errors, filename locale rules, local image resolution, and bundled backend startup.

Test behavior at module boundaries: translated IDs, catalog validation, plan replacement, persistence, shopping quantities, invalid dates, HTTP request contracts, and startup paths. Avoid tests that only repeat implementation details. Keep recipe catalogs unchanged and use temporary paths for tests that write data.

Python 3.14 uses Kivy 3 development wheels; Python 3.11–3.13 use Kivy 2.3.1. Kivy 3 widget tests and real event-loop checks passed at 100% and 200% scale; a visual review of the updated layout is still required before release. Kivy widgets must be changed only on the main event loop. Background threads may perform I/O and pass results through `Clock.schedule_once`.
