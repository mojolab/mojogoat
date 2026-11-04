"""Shared isolation for the REST API tests (goat-scoped API v2, ADR-016).

Every test gets a temp registry file, a temp MOJOGOAT_OPERATIONS_DIR, a temp
``mojogoatapi.DEFAULT_DATA_DIR`` (so goats created without ``goat_path`` never touch
/xpal-data), an empty operations store and an empty ``mojogoatapi._goat_cache``.
"""
import asyncio
import json
import os
import shutil
import tempfile

import mojogoatapi
from mojogoat import operations


class ApiEnv:
    """Context for one isolated API instance. Call start() / stop() (or use as a fixture)."""

    def start(self):
        self.root = tempfile.mkdtemp(prefix="mojogoat_api_test_")
        self.registry_file = os.path.join(self.root, "test_registry.json")
        self.data_dir = os.path.join(self.root, "goats")
        os.makedirs(self.data_dir)
        self.operations_dir = os.path.join(self.root, "operations")

        self._prev_ops_dir = os.environ.get("MOJOGOAT_OPERATIONS_DIR")
        os.environ["MOJOGOAT_OPERATIONS_DIR"] = self.operations_dir
        self._prev_data_dir = mojogoatapi.DEFAULT_DATA_DIR
        mojogoatapi.DEFAULT_DATA_DIR = self.data_dir

        mojogoatapi.app.config["TESTING"] = True
        mojogoatapi.app.config["DEBUG"] = False
        operations.reset_store()
        mojogoatapi._goat_cache.clear()
        mojogoatapi.initialize_app(self.registry_file)
        self.client = mojogoatapi.app.test_client()
        return self

    def stop(self):
        mojogoatapi._goat_cache.clear()
        operations.reset_store()
        mojogoatapi.DEFAULT_DATA_DIR = self._prev_data_dir
        if self._prev_ops_dir is None:
            os.environ.pop("MOJOGOAT_OPERATIONS_DIR", None)
        else:
            os.environ["MOJOGOAT_OPERATIONS_DIR"] = self._prev_ops_dir
        shutil.rmtree(self.root, ignore_errors=True)

    # -- helpers ---------------------------------------------------------

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def create_goat(self, name, goat_type="memory", **extra):
        """POST /api/goats and assert it was created; returns the response JSON."""
        body = {"name": name, "type": goat_type, **extra}
        r = self.client.post("/api/goats", json=body)
        assert r.status_code == 201, (r.status_code, r.get_json())
        return r.get_json()

    def create_text_goat(self, name):
        """Create a text goat under a temp dir; returns its path."""
        goat_path = self.path("text_" + name)
        self.create_goat(name, "text", goat_path=goat_path)
        return goat_path

    def cached_goat(self, name):
        """The GoatBase the server uses for *name* (resolved/cached through the server)."""
        return mojogoatapi.resolve_goat(name)

    def write_registry(self, content: dict):
        with open(self.registry_file, "w") as f:
            json.dump(content, f)
        mojogoatapi.initialize_app(self.registry_file)

    def read_registry_file(self):
        with open(self.registry_file) as f:
            return json.load(f)


def run(coro):
    """Run a goat coroutine from a sync test."""
    return asyncio.run(coro)
