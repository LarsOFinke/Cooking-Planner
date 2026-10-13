"""Install the Kivy line that supports the selected Python interpreter."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NIGHTLY_INDEX = "https://kivy.org/downloads/simple/"


def pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True, cwd=ROOT)


def main() -> None:
    if not (3, 11) <= sys.version_info[:2] <= (3, 14):
        raise SystemExit("Python 3.11–3.14 is required.")
    try:
        if sys.version_info[:2] == (3, 14):
            # Kivy's stable release has no CPython 3.14 wheel. Its nightly line does.
            pip("install", "--pre", "--no-deps", "--index-url", NIGHTLY_INDEX,
                "Kivy>=3.0.0.dev0")
            pip("install", "--pre", "--extra-index-url", NIGHTLY_INDEX,
                "-r", "src/requirements.txt")
        else:
            pip("install", "-r", "src/requirements.txt")
        pip("install", "-r", "src/requirements-dev.txt")
    except subprocess.CalledProcessError:
        raise SystemExit("Kivy installation failed. Python 3.14 needs access to the Kivy nightly wheel index; "
                         "check your network connection and rerun make dev.") from None


if __name__ == "__main__":
    main()
