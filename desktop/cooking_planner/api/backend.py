import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from cooking_planner.paths import bundle_root, catalog_directory


class BackendLauncher:
    def __init__(self, port: int, data_dir: Path) -> None:
        self.port = port
        self.data_dir = data_dir
        self.process: subprocess.Popen | None = None
        self.log = None
        self.instance_token = uuid4().hex

    def _healthy(self) -> bool:
        try:
            with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=1) as response:
                if response.status != 200:
                    return False
                health = json.load(response)
                return (health.get("status") == "ok" and
                        health.get("instanceToken") == self.instance_token)
        except (OSError, URLError, ValueError, AttributeError):
            return False

    def start(self) -> None:
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                raise RuntimeError(f"Backend port {self.port} is already in use. Choose another port in client.cfg.")
        except ConnectionRefusedError:
            pass
        root = bundle_root()
        frozen = getattr(sys, "frozen", False)
        jar = root / "backend.jar" if frozen else Path(os.getenv("COOKING_PLANNER_BACKEND_JAR", root / "backend" / "target" / "cooking-planner-api-0.1.0.jar"))
        catalogs = catalog_directory()
        if not jar.exists():
            raise RuntimeError("Backend JAR is missing. Build it with: mvn -f backend/pom.xml package")
        if not catalogs.is_dir():
            raise RuntimeError("Recipe catalogs are missing from the data directory")
        java = root / "runtime" / "bin" / ("java.exe" if os.name == "nt" else "java") if frozen else Path("java")
        if frozen and not java.is_file():
            raise RuntimeError("Bundled Java runtime is missing from this executable")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log = (self.data_dir / "backend.log").open("a", encoding="utf-8")
        environment = os.environ.copy()
        environment["COOKING_PLANNER_DATA_DIR"] = str(self.data_dir)
        environment["COOKING_PLANNER_PORT"] = str(self.port)
        environment["COOKING_PLANNER_CATALOG_DIR"] = str(catalogs)
        environment["COOKING_PLANNER_INSTANCE_TOKEN"] = self.instance_token
        self.process = subprocess.Popen([str(java), "-jar", str(jar)], stdout=self.log, stderr=subprocess.STDOUT, env=environment)
        for _ in range(240):
            if self.process.poll() is not None:
                break
            if self._healthy():
                return
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
