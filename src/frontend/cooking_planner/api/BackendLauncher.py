"""Run the separate Python backend on loopback for the desktop HTTP client."""

import json
import socket
from threading import Thread
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn

from cooking_planner.paths import catalog_directory
from cooking_planner_backend.app import create_app


class BackendLauncher:
    def __init__(self, port: int, data_dir: Path) -> None:
        self.port = port
        self.data_dir = data_dir
        self.instance_token = uuid4().hex
        self.server = None
        self.thread = None

    def _healthy(self) -> bool:
        try:
            request = Request(f'http://127.0.0.1:{self.port}/api/health',
                              headers={'X-Cooking-Planner-Token': self.instance_token})
            with urlopen(request, timeout=1) as response:
                health = json.load(response)
                return response.status == 200 and health.get('status') == 'ok'
        except (OSError, URLError, ValueError, AttributeError):
            return False

    def start(self) -> None:
        try:
            with socket.create_connection(('127.0.0.1', self.port), timeout=1):
                raise RuntimeError(f'Backend port {self.port} is already in use. Choose another port in client.cfg.')
        except ConnectionRefusedError:
            pass
        catalogs = catalog_directory()
        if not catalogs.is_dir():
            raise RuntimeError('Recipe catalogs are missing')
        app = create_app(self.data_dir, catalogs, self.instance_token)
        config = uvicorn.Config(app, host='127.0.0.1', port=self.port, log_level='warning', access_log=False)
        self.server = uvicorn.Server(config)
        self.thread = Thread(target=self.server.run, name='cooking-planner-api', daemon=True)
        self.thread.start()
        for _ in range(240):
            if not self.thread.is_alive():
                break
            if self._healthy():
                return
            time.sleep(0.25)
        self.stop()
        raise RuntimeError('Local Python backend did not start')

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)
        if self.server is not None:
            self.server.config.app.state.storage.close()
        self.server = None
        self.thread = None
