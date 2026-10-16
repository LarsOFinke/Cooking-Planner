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
- A new Linux AppImage was built locally and opened with temporary user data. The source app passed a real Kivy event-loop smoke across all five tabs at 100% and 200% scale. Windows and Android need fresh CI artifacts and installed runtime tests; the 2026-10-15 CI artifacts predate these changes. Linux still needs a complete installed user-flow check before release.
- All 586 bundled recipe image rights records remain pending. Clear them before distribution beyond private testing.
- Direct package versions and security-critical Starlette are pinned, but platform-specific transitive dependencies, OS packages, Android SDK components, and the Windows Inno Setup installer are not fully locked by digest. Record artifact hashes and resolved dependency lists for each release candidate.

The CI quality job now audits the resolved Python environment. For a local check, install the runtime, test, and build requirements in an isolated environment and run `python -m pip_audit` followed by `make quality`. The local Python 3.14 audit scanned 57 installed distributions and reported no known vulnerabilities; it could not identify the Kivy nightly wheel on PyPI, so that wheel requires separate provenance review. The PyPI advisory API reported no known advisories for the Android-specific direct pins.
