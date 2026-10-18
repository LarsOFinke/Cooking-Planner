import os
import re
import sys
from configparser import ConfigParser
from configparser import Error as ConfigError
from pathlib import Path

from cooking_planner.paths import catalog_directory, on_android
from cooking_planner.ui.window import fullscreen_mode, minimum_window_size

if not on_android():
    os.environ.setdefault("KIVY_DESKTOP_PATH_ID", "CookingPlanner")

def default_data_dir() -> Path:
    if on_android():
        from android.storage import app_storage_path

        return Path(app_storage_path()) / 'cooking-planner'
    return Path.home() / '.cooking-planner'


def prepare_data_directory(data_dir: Path, default_location: bool) -> None:
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if default_location and os.name == 'posix':
        data_dir.chmod(0o700)


def bounded_number(config: ConfigParser, section: str, key: str, default: int | float,
                   minimum: int | float, maximum: int | float) -> int | float:
    try:
        value = config.getint(section, key) if isinstance(default, int) else config.getfloat(section, key)
    except (ConfigError, ValueError, TypeError):
        return default
    return value if minimum <= value <= maximum else default


def preferred_locale(config: ConfigParser) -> str:
    available = sorted(path.stem[-2:] for path in catalog_directory().glob('recipes_??.json')
                       if re.fullmatch(r'recipes_[a-z]{2}\.json', path.name))
    preferred = config.get('ui', 'locale', fallback='en').lower()
    return preferred if preferred in available else ('en' if 'en' in available else (available[0] if available else 'en'))


def fullscreen_enabled(config: ConfigParser) -> bool:
    try:
        return config.getboolean('ui', 'fullscreen', fallback=False)
    except (ConfigError, ValueError):
        return False


def main() -> None:
    config = ConfigParser()
    configured_data_dir = os.getenv('COOKING_PLANNER_DATA_DIR')
    data_dir = Path(configured_data_dir) if configured_data_dir else default_data_dir()
    prepare_data_directory(data_dir, not configured_data_dir)
    config.read(data_dir / "client.cfg")
    scale = bounded_number(config, 'ui', 'scale', 1.0, 1.0, 2.0)
    if scale not in (1.0, 1.25, 1.5, 1.75, 2.0):
        scale = 1.0
    if not on_android():
        from kivy.config import Config

        minimum_width, minimum_height = minimum_window_size(scale)
        Config.set('graphics', 'minimum_width', str(minimum_width))
        Config.set('graphics', 'minimum_height', str(minimum_height))
        Config.set('graphics', 'width', str(max(minimum_width, bounded_number(
            config, 'ui', 'window_width', 1280, 900, 3840))))
        Config.set('graphics', 'height', str(max(minimum_height, bounded_number(
            config, 'ui', 'window_height', 820, 650, 2160))))
        mode = fullscreen_mode(fullscreen_enabled(config))
        Config.set('graphics', 'fullscreen', mode if isinstance(mode, str) else ('1' if mode else '0'))

    from cooking_planner_backend.core.LocalPlanner import LocalPlanner

    from cooking_planner.CookingPlannerApp import CookingPlannerApp

    planner = None
    try:
        startup_error = None
        try:
            planner = LocalPlanner(data_dir, catalog_directory())
        except (OSError, RuntimeError, ValueError) as error:
            startup_error = str(error)
            print(f'Local planner startup failed: {startup_error}', file=sys.stderr)
        CookingPlannerApp(planner,
                          startup_error=startup_error, config_path=data_dir / "client.cfg", ui_scale=scale,
                          ui_locale=preferred_locale(config)).run()
    finally:
        if planner is not None:
            planner.close()
