"""Tests for the operations.py persistence addition (ADR-014): operations
survive a process restart by being write-through cached to disk under
MOJOGOAT_OPERATIONS_DIR, and reloaded via load_persisted().

Operations are scoped to a goat (ADR-016): tests pass ``goat=`` so a reload accepts them, and
files without a ``goat`` field are skipped (warned about) and left on disk."""
import json
import logging
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
    op = operations.create_operation("test_op", ["a"], {}, goat="g1")
    path = tmp_path / f"{op['operation_id']}.json"
    assert path.exists()


def test_post_results_updates_persisted_file(tmp_path):
    op = operations.create_operation("test_op", [], {}, goat="g1")
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    path = tmp_path / f"{op['operation_id']}.json"
    on_disk = json.loads(path.read_text())
    assert on_disk["status"] == "awaiting_validation"
    assert len(on_disk["results"]) == 1


def test_load_persisted_reloads_after_simulated_restart(tmp_path):
    op = operations.create_operation("test_op", [], {}, goat="g1")
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    # Simulate a process restart: clear the in-memory store, keep the files.
    operations.reset_store()
    assert operations.get_operation(op["operation_id"], goat="g1") is None

    loaded = operations.load_persisted()

    assert loaded == 1
    reloaded = operations.get_operation(op["operation_id"], goat="g1")
    assert reloaded is not None
    assert reloaded["status"] == "awaiting_validation"
    assert reloaded["goat"] == "g1"
    # ...and it is only reachable under its own goat
    assert operations.get_operation(op["operation_id"], goat="g2") is None


def test_delete_operation_removes_persisted_file(tmp_path):
    op = operations.create_operation("test_op", [], {}, goat="g1")
    path = tmp_path / f"{op['operation_id']}.json"
    assert path.exists()

    operations.delete_operation(op["operation_id"])

    assert not path.exists()


def test_load_persisted_does_not_clobber_in_memory_operation(tmp_path):
    """If an op_id is already in memory (e.g. created after a partial reload),
    load_persisted must not overwrite it with a stale on-disk copy."""
    op = operations.create_operation("test_op", [], {}, goat="g1")
    operations.post_results(op["operation_id"], [{"type": "add_node", "payload": {"nodeid": "a"}}])

    loaded = operations.load_persisted()

    assert loaded == 0
    assert operations.get_operation(op["operation_id"], goat="g1")["status"] == "awaiting_validation"



def test_create_operation_persists_goat_field(tmp_path):
    op = operations.create_operation("test_op", [], {}, goat="g1")
    assert op["goat"] == "g1"
    on_disk = json.loads((tmp_path / f"{op['operation_id']}.json").read_text())
    assert on_disk["goat"] == "g1"


def test_load_persisted_skips_files_without_goat_and_leaves_them(tmp_path, caplog):
    """Pre-ADR-016 files have no 'goat': skipped with a warning, left on disk untouched."""
    legacy = {"operation_id": "legacy-op-1", "name": "old", "status": "awaiting_validation",
              "node_ids": [], "params": {}, "results": [], "created": "2026-01-01T00:00:00",
              "updated": "2026-01-01T00:00:00"}
    legacy_path = tmp_path / "legacy-op-1.json"
    legacy_path.write_text(json.dumps(legacy, indent=2))
    legacy_bytes = legacy_path.read_bytes()

    current = operations.create_operation("new", [], {}, goat="g1")
    operations.reset_store()  # simulated restart; both files stay on disk

    with caplog.at_level(logging.WARNING, logger="mojogoat.operations"):
        loaded = operations.load_persisted()

    assert loaded == 1
    assert operations.get_operation(current["operation_id"], goat="g1") is not None
    assert operations.get_operation("legacy-op-1") is None
    assert operations.list_operations() and len(operations.list_operations()) == 1
    assert legacy_path.exists() and legacy_path.read_bytes() == legacy_bytes
    assert any("legacy-op-1.json" in r.getMessage() for r in caplog.records)


def test_load_persisted_skips_empty_goat_field(tmp_path):
    op = {"operation_id": "blank-goat-op", "goat": "", "name": "x", "status": "pending",
          "node_ids": [], "params": {}, "results": [], "created": "t", "updated": "t"}
    path = tmp_path / "blank-goat-op.json"
    path.write_text(json.dumps(op))

    assert operations.load_persisted() == 0
    assert path.exists()


def test_operations_are_listed_and_deleted_per_goat(tmp_path):
    a = operations.create_operation("a_op", [], {}, goat="ga")
    b = operations.create_operation("b_op", [], {}, goat="gb")

    assert [o["operation_id"] for o in operations.list_operations("ga")] == [a["operation_id"]]
    assert [o["operation_id"] for o in operations.list_operations("gb")] == [b["operation_id"]]

    # wrong goat: not found, not deleted, file kept
    assert operations.delete_operation(a["operation_id"], goat="gb") is False
    assert (tmp_path / f"{a['operation_id']}.json").exists()
    assert operations.post_results(a["operation_id"], [], goat="gb") is None
    assert operations.validate_result(a["operation_id"], "r", "accept", goat="gb") is None
    assert operations.delete_operation(a["operation_id"], goat="ga") is True
