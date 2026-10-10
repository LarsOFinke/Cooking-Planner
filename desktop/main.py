import os
from configparser import ConfigParser
from pathlib import Path

from cooking_planner.ApiClient import ApiClient
from cooking_planner.BackendLauncher import BackendLauncher
from cooking_planner.CookingPlannerApp import CookingPlannerApp


if __name__ == "__main__":
    config = ConfigParser()
    data_dir = Path(os.getenv("COOKING_PLANNER_DATA_DIR", Path.home() / ".cooking-planner"))
    config.read(data_dir / "client.cfg")
    port = int(os.getenv("COOKING_PLANNER_PORT", config.get("backend", "port", fallback="8765")))
    launcher = BackendLauncher(port, data_dir)
    try:
        startup_error = None
        try:
            launcher.start()
        except (OSError, RuntimeError) as error:
            startup_error = str(error)
        CookingPlannerApp(ApiClient(f"http://127.0.0.1:{port}"), startup_error=startup_error).run()
    finally:
        launcher.stop()
