import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


class BackendLauncher:
    def __init__(self, port: int, data_dir: Path) -> None:
        self.port = port
        self.data_dir = data_dir
        self.process: subprocess.Popen | None = None
        self.log = None

    def _healthy(self) -> bool:
        try:
            with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=1) as response:
                return response.status == 200
        except (OSError, URLError):
            return False

    def start(self) -> None:
        if self._healthy():
            return
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        jar = root / "backend.jar" if getattr(sys, "frozen", False) else root / "backend" / "target" / "cooking-planner-api-0.1.0.jar"
        if not jar.exists():
            raise RuntimeError("Backend JAR is missing. Build it with: mvn -f backend/pom.xml package")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log = (self.data_dir / "backend.log").open("a", encoding="utf-8")
        environment = os.environ.copy()
        environment["COOKING_PLANNER_DATA_DIR"] = str(self.data_dir)
        environment["COOKING_PLANNER_PORT"] = str(self.port)
        self.process = subprocess.Popen(["java", "-jar", str(jar)], stdout=self.log, stderr=subprocess.STDOUT, env=environment)
        for _ in range(40):
            if self._healthy():
                return
            if self.process.poll() is not None:
                break
            time.sleep(0.25)
        self.stop()
        raise RuntimeError(f"Backend did not start. See {self.data_dir / 'backend.log'}")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.log is not None:
            self.log.close()
