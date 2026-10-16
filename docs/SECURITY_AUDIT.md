# Security audit — 2026-10-16

This review covers application dependencies, packaging tools, CI actions, and access to the local API. It does not certify an installed artifact or the rights to publish bundled images.

Evidence: the [last successful CI run](https://github.com/LarsOFinke/Cooking-Planner/actions/runs/38761630159), [GitHub's Node 20 retirement notice](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/), and the [Starlette advisory database](https://github.com/advisories?query=ecosystem%3Apip+starlette). Version availability was checked against PyPI release metadata on the audit date.

## Findings and changes

| Area | Finding | Change |
| --- | --- | --- |
| Local API | Loopback binding alone allowed another local process to read and change recipes, plans, ingredients, and prices. The health endpoint returned the instance token. | Require a random per-launch token in an HTTP header for every route, including health. Health now returns only a status. |
| Python web stack | The old FastAPI constraint resolved Starlette 0.46.2, which the Python advisory database reports as vulnerable. | Pin FastAPI 0.143.2 and Starlette 1.8.0 for desktop and Android. |
| GitHub Actions | The last successful workflow warned that checkout v4 and upload-artifact v4 target retired Node 20; setup-java v4 separately reported deprecation. There is no npm dependency or npm install in this repository. | Pin current Node 24 action releases by full commit SHA: checkout 7.0.1, setup-python 7.0.0, upload-artifact 7.0.2, setup-java 6.1.0. Disable persisted checkout credentials. |
| Build resolution | Broad version ranges and moving Android Git branches made future artifacts hard to reproduce. | Pin direct Python dependencies and packaging tools. Pin the Buildozer and python-for-android commits used by the successful 2026-10-15 Android build. |
| Windows packaging | CI installed whichever Inno Setup version Chocolatey offered at build time. | Pin the CI package to the approved 6.7.1 release. |
| pip | The local environment had pip 25.1.1, which the advisory database flagged. | Use pip 26.2.1 in development and package build environments. CI installs it before dependencies. |

The desktop pins are in `src/requirements.txt`, `src/requirements-build.txt`, and `src/requirements-dev.txt`. Android uses a separate set in `scripts/build/android/buildozer.spec` because its compiled Pydantic core and SQLAlchemy recipes must match the Android toolchain. The Pydantic 2.12.3 / core 2.41.4 pair and SQLAlchemy 2.0.30 remain on the versions used by the successful APK build. PyPI reports no known advisories for those pins. A published advisory scan is a useful gate, not proof that a package has no undiscovered flaw.

## Remaining release work

- Python 3.14 desktop builds still need Kivy 3.0.0.dev0 from Kivy's nightly index. Kivy 2.3.1 is pinned for Python 3.11–3.13 and for Android. A stable desktop build should use Python 3.13 until a stable Kivy release supports 3.14.
- The Android toolchain is pinned to the revisions that built the previous APK, but python-for-android's `develop` branch remains a development line. The new FastAPI and Starlette versions require a fresh Android build and device runtime test.
- A new Linux AppImage was built locally and opened with temporary user data. The source app passed a real Kivy event-loop smoke across all five tabs at 100% and 200% scale. The 2026-10-16 CI run built all three artifacts successfully. This later privacy review requires another build before using any of those artifacts for private testing. Installed runtime tests remain necessary on each platform.
- All 586 bundled recipe image rights records remain pending. Clear them before distribution beyond private testing.
- Direct package versions and security-critical Starlette are pinned, but platform-specific transitive dependencies, OS packages, Android SDK components, and the Windows Inno Setup installer are not fully locked by digest. Record artifact hashes and resolved dependency lists for each release candidate.

The CI quality job now audits the resolved Python environment. For a local check, install the runtime, test, and build requirements in an isolated environment and run `python -m pip_audit` followed by `make quality`. The local Python 3.14 audit scanned 57 installed distributions and reported no known vulnerabilities; it could not identify the Kivy nightly wheel on PyPI, so that wheel requires separate provenance review. The PyPI advisory API reported no known advisories for the Android-specific direct pins.

## Source and artifact review — 2026-10-16

The [successful three-platform CI run](https://github.com/LarsOFinke/Cooking-Planner/actions/runs/38838699344) built commit `a0a6d8f`. Its artifacts were downloaded separately for inspection. They **precede** the fixes below and should not be treated as the next private test build.

| Check | Result |
| --- | --- |
| Application network paths | The frontend HTTP client and backend health probe are the only automatic application HTTP calls; both target `127.0.0.1`. Uvicorn binds to that address. The recipe credit link opens a browser only when clicked; all 586 bundled credit `source_url` fields are empty. No application code for telemetry uploads, update checks, email, or shell commands was found. |
| Runtime network trace | A 10-second source-app startup under `strace -f -e trace=network` used temporary user data. All 45 recorded IPv4 address occurrences were `127.0.0.1`; there were no IPv6 sockets. This covers startup, not every interactive action or bundled native-library behavior. |
| Android artifact | All 82 packaged application `.pyc` files matched bytecode compiled from commit `a0a6d8f` with the packaging optimization setting. All 591 packaged catalog/image files matched repository bytes. The APK requested only `INTERNET`, needed for loopback HTTP. Its manifest also had `allowBackup=true`, now changed in the Buildozer spec. |
| Linux artifact | PyInstaller archive listing contained the expected application packages and Python dependencies; no unexpected application module name appeared. All 592 packaged catalog/image files matched repository bytes. The application bytecode was not compared because this machine does not have the CI build's Python 3.13 interpreter. |
| Windows artifact | CI built the installer from the PyInstaller output and the checked-in Inno Setup script. The local Inno extractor and 7-Zip could not parse this Inno Setup 6.7.1 installer, so its compressed payload has not been independently enumerated here. A Windows installation and file inventory are still needed. |
| Image files | All 586 tracked PNG files had valid PNG structure and an `IEND` at end of file, with no text/EXIF chunks or trailing bytes. This does not prove that an image decoder has no vulnerability. |

The review identified four privacy issues and changed the source/build settings:

1. `urllib.request.urlopen` could obey an inherited HTTP proxy even for `127.0.0.1`, which could expose the local API token and requests. The client and health probe now use a proxy-free opener restricted to loopback. They reject redirects, which otherwise forward ordinary request headers to the redirected destination. [Python documents both behaviors](https://docs.python.org/3/library/urllib.request.html).
2. FastAPI 0.143.2 includes OpenTelemetry hooks. Exporter setup is normally opt-in, but an inherited `FASTAPI_OTEL_AUTO_CONFIGURE=true` and a configured exporter could enable it. The app now disables traces, metrics, logs, operation spans, and automatic setup explicitly. [FastAPI describes these settings](https://fastapi.tiangolo.com/advanced/opentelemetry/).
3. Buildozer's default `android.allow_backup=True` appeared in the APK manifest. The spec now sets it to `False`, and CI verifies the built manifest and permission list. This disables Android cloud backup, though Android notes some Android 12+ devices can still allow device-to-device transfer despite `allowBackup=false`. [Android backup documentation](https://developer.android.com/identity/data/autobackup).
4. The existing default user-data directory on the audit machine had mode `775`, and personal data files had mode `664`. A group member could read or change them if that group were shared. The launcher now creates data directories with mode `700` and tightens the existing default directory to `700` on POSIX systems before reading settings or starting the backend. Existing explicitly configured data directories retain their chosen permissions. The audit did not change the machine's existing user files directly.

The source app passed `make quality` with 90 tests after these changes (frontend 88.0% and backend 83.6% line coverage). Focused tests exercised proxy bypass and redirect rejection with real loopback sockets, and checked data-directory permissions. A static review and a clean dependency advisory scan cannot prove a binary malware-free: compiled Kivy/Python/native dependencies, Android toolchains, and the Windows installer are third-party code. Transitive package hashes and full artifact provenance are not yet locked, and the Python 3.14 Kivy wheel is a development build. Treat the next CI artifacts as new candidates requiring manifest checks, installed smoke tests, and recorded SHA-256 hashes.
