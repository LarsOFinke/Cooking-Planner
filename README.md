# Cooking Planner V1 prototype

A local desktop cooking planner. Add recipes, import language-specific JSON arrays, switch recipe language, inspect recipes, and assign one recipe to each breakfast, lunch, or dinner slot. Data remains on this computer.

## Run

Requirements: Java 21, Maven 3.6.3+, and Python 3.11–3.13 with Kivy 2.3.1. Build and start from the repository root:

```bash
mvn -f backend/pom.xml package
python3.13 -m venv .venv
.venv/bin/pip install -r desktop/requirements.txt
.venv/bin/python desktop/main.py
```

On Windows use `py -3.13 -m venv .venv`, `.venv\Scripts\pip install -r desktop\requirements.txt`, and `.venv\Scripts\python desktop\main.py`. The desktop launcher starts and stops its own loopback Spring Boot process. A Java runtime must be available on `PATH`.

Data defaults to `~/.cooking-planner/` on Linux and `%USERPROFILE%\.cooking-planner\` on Windows. Override it with `COOKING_PLANNER_DATA_DIR`. The `recipes_*.json` and `plans.json` files are application data; copy them all for a backup while the app is closed. Existing `recipes.json` is read as English until the first English edit/import copies it to `recipes_en.json`. To override the port, set `COOKING_PLANNER_PORT` or copy [desktop/client.cfg.example](desktop/client.cfg.example) to `<data directory>/client.cfg`. Environment variables take precedence.

## Recipe JSON

The import box accepts paths named `recipes_en.json`, `recipes_de.json`, and so on. The two-letter suffix determines the catalog. Choose a file containing a UTF-8 array of up to 500 recipe objects. Example `recipes_en.json`:

```json
[
  {
    "title": "Tomato soup",
    "category": "Dinner",
    "ingredients": ["4 tomatoes", "salt"],
    "instructions": "Simmer and blend.",
    "prepMinutes": 25
  }
]
```

Every field is required. Import each language file separately, then use the language selector above the recipe list. Imports append new recipes and assign IDs; import the same file twice to create duplicates. The incoming file is never modified. Recipe catalogs remain independent. Existing planned meals keep the recipe language in which they were created; matching translations across files would require a shared recipe key that the current data contract does not define. The app controls remain in English in V1.

## Build a desktop executable

The first packaged target is a PyInstaller executable built **on each target operating system**. It includes the Python/Kivy client and backend JAR; it needs Java 21 installed. Install `pyinstaller` in the desktop virtual environment, then run:

```bash
# Linux
.venv/bin/pyinstaller --onefile --windowed --name CookingPlanner --paths desktop --add-data "backend/target/cooking-planner-api-0.1.0.jar:backend.jar" desktop/main.py
```

```powershell
# Windows PowerShell, after building the JAR
.venv\Scripts\pyinstaller --onefile --windowed --name CookingPlanner --paths desktop --add-data "backend/target/cooking-planner-api-0.1.0.jar;backend.jar" desktop/main.py
```

Outputs are under `dist/`. These packaging commands are prepared but no Windows build has been verified here. A fully self-contained installer would also package a Java runtime, which is a later release task.

## Scope and architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). V1 is intentionally single-user and local. There is no account system, shopping list, nutrition model, recipe deduplication, or sync. The server listens only on `127.0.0.1` and has no authentication; do not expose it on a network interface.

## Checks performed

Five Java tests pass, covering file persistence, locale separation, old-file compatibility, rejected imports, and the HTTP contract through Spring's mock servlet. Two Python suffix tests and Python syntax checks pass. Run `mvn -f backend/pom.xml test` and `python -m unittest discover -s desktop/tests` on your machine. The current sandbox blocks local sockets and has no display server, so a live HTTP process and full Kivy event loop must also be checked on a normal desktop before relying on the prototype.
