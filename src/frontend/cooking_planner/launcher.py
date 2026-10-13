import os
import sys
from configparser import ConfigParser
from pathlib import Path

from cooking_planner.paths import on_android

if not on_android():
    os.environ.setdefault("KIVY_DESKTOP_PATH_ID", "CookingPlanner")

from kivy.config import Config  # noqa: E402

if not on_android():
    Config.set("graphics", "minimum_width", "900")
    Config.set("graphics", "minimum_height", "650")
    Config.set("graphics", "width", "1280")
    Config.set("graphics", "height", "820")

from cooking_planner.api.ApiClient import ApiClient  # noqa: E402
from cooking_planner.api.BackendLauncher import BackendLauncher  # noqa: E402
from cooking_planner.CookingPlannerApp import CookingPlannerApp  # noqa: E402


def default_data_dir() -> Path:
    if on_android():
        from android.storage import app_storage_path

        return Path(app_storage_path()) / 'cooking-planner'
    return Path.home() / '.cooking-planner'


def main() -> None:
    config = ConfigParser()
    configured_data_dir = os.getenv('COOKING_PLANNER_DATA_DIR')
    data_dir = Path(configured_data_dir) if configured_data_dir else default_data_dir()
    config.read(data_dir / "client.cfg")
    port = int(os.getenv("COOKING_PLANNER_PORT", config.get("backend", "port", fallback="8765")))
    launcher = BackendLauncher(port, data_dir)
    try:
        startup_error = None
        try:
            launcher.start()
        except (OSError, RuntimeError) as error:
            startup_error = str(error)
            print(f'Local backend startup failed: {startup_error}', file=sys.stderr)
        scale = config.getfloat("ui", "scale", fallback=1.0)
        if scale not in (1.0, 1.25, 1.5, 1.75, 2.0):
            scale = 1.0
        CookingPlannerApp(ApiClient(f"http://127.0.0.1:{port}"), startup_error=startup_error,
                          config_path=data_dir / "client.cfg", ui_scale=scale).run()
    finally:
        launcher.stop()
