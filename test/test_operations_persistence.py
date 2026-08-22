"""Tests for the operations.py persistence addition (ADR-0014): operations
survive a process restart by being write-through cached to disk under
MOJOGOAT_OPERATIONS_DIR, and reloaded via load_persisted()."""
import os

import pytest

from mojogoat import operations


@pytest.fixture(autouse=True)
def isolated_operations_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MOJOGOAT_OPERATIONS_DIR", str(tmp_path))
    operations.reset_store()
    yield
    operations.reset_store()


def test_create_operation_persists_to_disk(tmp_path):
    op = operations.create_operation("test_op", ["a"], {})
    path = tmp_path / f"{op['operation_id']}.json"
    assert path.exists()


def test_post_results_updates_persisted_file(tmp_path):
    op = operations.create_operation("test_op", [], {})
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    path = tmp_path / f"{op['operation_id']}.json"
    import json
    on_disk = json.loads(path.read_text())
    assert on_disk["status"] == "awaiting_validation"
    assert len(on_disk["results"]) == 1


def test_load_persisted_reloads_after_simulated_restart(tmp_path):
    op = operations.create_operation("test_op", [], {})
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    # Simulate a process restart: clear the in-memory store, keep the files.
    operations.reset_store()
    assert operations.get_operation(op["operation_id"]) is None

    loaded = operations.load_persisted()

    assert loaded == 1
    reloaded = operations.get_operation(op["operation_id"])
    assert reloaded is not None
    assert reloaded["status"] == "awaiting_validation"


def test_delete_operation_removes_persisted_file(tmp_path):
    op = operations.create_operation("test_op", [], {})
    path = tmp_path / f"{op['operation_id']}.json"
    assert path.exists()

    operations.delete_operation(op["operation_id"])

    assert not path.exists()


def test_load_persisted_does_not_clobber_in_memory_operation(tmp_path):
    """If an op_id is already in memory (e.g. created after a partial reload),
    load_persisted must not overwrite it with a stale on-disk copy."""
    op = operations.create_operation("test_op", [], {})
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    loaded = operations.load_persisted()

    assert loaded == 0
    assert operations.get_operation(op["operation_id"])["status"] == "awaiting_validation"
