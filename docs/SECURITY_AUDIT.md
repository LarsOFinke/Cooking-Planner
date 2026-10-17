# Security review

## Current application boundary

The Kivy application calls `LocalPlanner` in process. Its feature stores read bundled recipe catalogs and write plans, shopping drafts, recipe edits, images, and SQLite data under the configured user data directory. The app starts no HTTP server, binds no port, and has no HTTP client for local data operations. Recipe credit links may open a browser when the user selects one.

The Android Buildozer spec requests no application permissions and sets `android.allow_backup = False`. The APK packaging check rejects any declared application permission and verifies `allowBackup=false`. These checks cover the source and manifest settings; an installed Android build still needs device testing.

The launcher creates the default user data directory with mode `0700` on POSIX and tightens an existing default directory before loading settings. A directory explicitly chosen with `COOKING_PLANNER_DATA_DIR` retains its owner's permission policy. The app preserves read-only bundled catalogs and writes user edits to its data directory. Close the app before copying data for backup.

## Verification and release limits

- `make quality` checks syntax, Ruff, tests, and separate frontend and backend coverage floors. CI also runs `pip-audit` on its resolved Python environment. Advisory scans cannot establish that dependencies are free of undisclosed vulnerabilities.
- The local service migration was tested with direct persistence tests and Kivy event-loop checks at 100% and 200% scale. A Linux executable and AppImage built successfully. Windows and Android packages need builds and installed runtime checks on their target platforms before release.
- All 586 bundled recipe image rights records remain pending. Review those rights before distributing the images beyond private testing.
- Runtime and build dependencies are pinned directly, but platform-specific transitive dependencies, OS packages, Android SDK components, and installer payloads are not fully locked by digest. Record resolved dependencies and artifact hashes for release candidates.

The earlier HTTP-era audit, including its artifact evidence and fixes, remains available in the repository history. Its loopback token, proxy, FastAPI, and Starlette findings no longer describe the current application.
