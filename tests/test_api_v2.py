"""Tests for the goat-scoped REST API behaviour introduced by ADR-016 (API v2).

Covers: goat isolation, 404 for unknown/invalid goats, 410 stubs for removed routes, absence of
server-wide state, scoped operations, goat-name and path validation, legacy registry handling,
status/health shape, and goat cache lifecycle. The migrated v1 tests live in test_api.py and
test_api_crud.py.
"""
import json
import logging
import os
import re

import pytest

import mojogoatapi
from mojogoat import operations
from api_support import ApiEnv, run


@pytest.fixture
def env():
    e = ApiEnv().start()
    yield e
    e.stop()


@pytest.fixture
def client(env):
    return env.client


def _status_without_timestamp(client):
    data = client.get("/api/status").get_json()
    data.pop("timestamp", None)
    return data


# ----------------------------------------------------------------------
# Isolation between goats
# ----------------------------------------------------------------------

def test_two_text_goats_stay_isolated_under_interleaved_writes(env, client):
    path1 = env.create_text_goat("iso1")
    path2 = env.create_text_goat("iso2")
    assert path1 != path2

    def post(goat, kind, body):
        r = client.post(f"/api/goats/{goat}/{kind}", json=body)
        assert r.status_code == 201, r.get_json()
        return r.get_json()

    # strictly alternating writes
    post("iso1", "nodes", {"nodeid": "a", "labels": ["One"]})
    post("iso2", "nodes", {"nodeid": "c", "labels": ["Two"]})
    post("iso1", "nodes", {"nodeid": "b", "labels": ["One"]})
    post("iso2", "nodes", {"nodeid": "d", "labels": ["Two"]})
    post("iso1", "nodes", {"nodeid": "shared", "who": "one"})
    post("iso2", "nodes", {"nodeid": "shared", "who": "two"})
    post("iso1", "relationships", {"source": "a", "target": "b", "story": "ONE_STORY"})
    post("iso2", "relationships", {"source": "c", "target": "d", "story": "TWO_STORY"})

    def ids(goat):
        return {n["nodeid"] for n in client.get(f"/api/goats/{goat}/nodes").get_json()}

    assert ids("iso1") == {"a", "b", "shared"}
    assert ids("iso2") == {"c", "d", "shared"}
    assert client.get("/api/goats/iso1/nodes/shared").get_json()["who"] == "one"
    assert client.get("/api/goats/iso2/nodes/shared").get_json()["who"] == "two"

    r1 = client.get("/api/goats/iso1/relationships").get_json()
    r2 = client.get("/api/goats/iso2/relationships").get_json()
    assert [r["story"] for r in r1] == ["ONE_STORY"]
    assert [r["story"] for r in r2] == ["TWO_STORY"]
    assert client.get("/api/goats/iso1/taxonomy").get_json() == {"ONE_STORY": 1}
    assert client.get("/api/goats/iso2/taxonomy").get_json() == {"TWO_STORY": 1}
    assert client.get("/api/goats/iso1/composition").get_json().get("Two") is None

    # a relationship cannot be read through the other goat
    assert client.get(f"/api/goats/iso2/relationships/{r1[0]['relationship_id']}").status_code == 404

    # data really lives in each goat's own directory
    assert os.path.isdir(path1) and os.path.isdir(path2)
    for goat, expected in (("iso1", (2 + 1, 1)), ("iso2", (2 + 1, 1))):
        s = client.get(f"/api/goats/{goat}/summary").get_json()
        assert (s["node_count"], s["rel_count"]) == expected


def test_scoped_calls_never_change_server_wide_state(env, client):
    env.create_text_goat("sw1")
    env.create_goat("sw2", "memory")
    before_goats = client.get("/api/goats").get_json()
    before_status = _status_without_timestamp(client)
    before_registry = client.get("/api/registry").get_json()
    before_health = client.get("/health").get_json()
    before_file = env.read_registry_file()

    for goat in ("sw1", "sw2", "sw1"):
        base = f"/api/goats/{goat}"
        assert client.post(f"{base}/nodes", json={"nodeid": "n1", "labels": ["L"]}).status_code == 201
        assert client.post(f"{base}/nodes", json={"nodeid": "n2"}).status_code == 201
        assert client.put(f"{base}/nodes/n1", json={"x": 1}).status_code == 200
        rel = client.post(f"{base}/relationships",
                          json={"source": "n1", "target": "n2", "story": "S"}).get_json()
        assert client.patch(f"{base}/relationships/{rel['relationship_id']}",
                            json={"k": "v"}).status_code == 200
        for suffix in ("nodes", "nodes/n1", "nodes/label/L", "relationships", "graph",
                       "composition", "taxonomy", "operations", "summary"):
            assert client.get(f"{base}/{suffix}").status_code == 200
        op = client.post(f"{base}/operations", json={"name": "o", "node_ids": []}).get_json()
        assert client.delete(f"{base}/operations/{op['operation_id']}").status_code == 200
        assert client.delete(f"{base}/relationships/{rel['relationship_id']}").status_code == 200
        assert client.delete(f"{base}/nodes/n2").status_code == 200
        # an unknown goat in between must not disturb anything either
        assert client.get("/api/goats/ghost/nodes").status_code == 404

    assert client.get("/api/goats").get_json() == before_goats
    assert _status_without_timestamp(client) == before_status
    assert client.get("/api/registry").get_json() == before_registry
    assert client.get("/health").get_json() == before_health
    assert env.read_registry_file() == before_file
    for g in before_goats["goats"]:
        assert "active" not in g and "default" not in g


# ----------------------------------------------------------------------
# Unknown and invalid goat names on scoped routes
# ----------------------------------------------------------------------

SCOPED_ROUTES = [
    ("GET", "nodes"), ("POST", "nodes"),
    ("GET", "nodes/n1"), ("PUT", "nodes/n1"), ("DELETE", "nodes/n1"),
    ("GET", "nodes/label/L"),
    ("GET", "relationships"), ("POST", "relationships"),
    ("GET", "relationships/r1"), ("PATCH", "relationships/r1"), ("DELETE", "relationships/r1"),
    ("GET", "graph"), ("GET", "composition"), ("GET", "taxonomy"),
    ("POST", "dump-relationships"), ("POST", "import-relationships"), ("POST", "compact"),
    ("GET", "operations"), ("POST", "operations"),
    ("GET", "operations/o1"), ("DELETE", "operations/o1"),
    ("POST", "operations/o1/results"), ("POST", "operations/o1/validate"),
]


def _call(client, method, path):
    return client.open(path, method=method, json={"nodeid": "n1", "name": "o", "filename": "/x",
                                                   "source": "a", "target": "b", "story": "s",
                                                   "result_id": "r", "action": "accept"})


@pytest.mark.parametrize("method,suffix", SCOPED_ROUTES)
def test_unknown_goat_is_404_on_every_scoped_route(client, method, suffix):
    r = _call(client, method, f"/api/goats/no_such_goat/{suffix}")
    assert r.status_code == 404
    assert r.get_json() == {"error": "Goat 'no_such_goat' not found"}


@pytest.mark.parametrize("method,suffix", SCOPED_ROUTES)
def test_registered_goat_that_was_deleted_is_404(env, client, method, suffix):
    env.create_goat("shortlived", "memory")
    assert client.get("/api/goats/shortlived/nodes").status_code == 200
    assert client.delete("/api/goats/shortlived").status_code == 200
    r = _call(client, method, f"/api/goats/shortlived/{suffix}")
    assert r.status_code == 404


INVALID_NAMES = ["-lead", "_lead", "a.b", "with space", "x" * 65, "é", "goat-é", "ünï"]


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_invalid_goat_name_in_url_is_404(client, name):
    for path in (f"/api/goats/{name}/nodes", f"/api/goats/{name}/operations",
                 f"/api/goats/{name}"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.get_json()["error"].startswith("Goat '")
    assert client.post(f"/api/goats/{name}/nodes", json={"nodeid": "n"}).status_code == 404


@pytest.mark.parametrize("path", ["/api/goats/..%2Fx/nodes", "/api/goats/../x/nodes",
                                  "/api/goats/%2E%2E/nodes"])
def test_dotdot_goat_name_in_url_never_resolves(client, path):
    r = client.get(path)
    assert r.status_code in (404, 410)  # path traversal never reaches a goat
    assert r.status_code != 200


def test_registry_entry_with_invalid_name_is_unreachable_and_warned_about(env, client, caplog):
    entry = {"name": "bad name", "type": "memory", "created": "2026-01-01T00:00:00"}
    with caplog.at_level(logging.WARNING, logger=mojogoatapi.app.logger.name):
        env.write_registry({"goats": [entry]})
    assert any("bad name" in r.getMessage() for r in caplog.records)

    # still in the registry (not renamed or deleted)...
    assert [g["name"] for g in client.get("/api/goats").get_json()["goats"]] == ["bad name"]
    # ...but not reachable through the scoped routes
    assert client.get("/api/goats/bad%20name/nodes").status_code == 404
    assert client.get("/api/goats/bad%20name").status_code == 404
    assert env.read_registry_file()["goats"][0]["name"] == "bad name"


# ----------------------------------------------------------------------
# Removed routes -> 410
# ----------------------------------------------------------------------

REMOVED = [
    ("GET", "/api/active-goat", "GET /api/goats/<name>"),
    ("POST", "/api/active-goat", "GET /api/goats/<name>"),
    ("GET", "/api/active-goat/composition", "/api/goats/<goat>/composition"),
    ("GET", "/api/active-goat/taxonomy", "/api/goats/<goat>/taxonomy"),
    ("POST", "/api/active-goat/dump-relationships", "/api/goats/<goat>/dump-relationships"),
    ("POST", "/api/active-goat/import-relationships", "/api/goats/<goat>/import-relationships"),
    ("POST", "/api/active-goat/compact", "/api/goats/<goat>/compact"),
    ("GET", "/api/active-goat/anything/else", "/api/goats/<goat>/anything/else"),
    ("GET", "/api/backend", "POST /api/goats"),
    ("POST", "/api/backend", "POST /api/goats"),
    ("GET", "/api/direct/nodes", "/api/goats/<goat>/nodes"),
    ("GET", "/api/debug", "no replacement"),
    ("GET", "/api/nodes", "/api/goats/<goat>/nodes"),
    ("POST", "/api/nodes", "/api/goats/<goat>/nodes"),
    ("GET", "/api/nodes/n1", "/api/goats/<goat>/nodes/n1"),
    ("PUT", "/api/nodes/n1", "/api/goats/<goat>/nodes/n1"),
    ("DELETE", "/api/nodes/n1", "/api/goats/<goat>/nodes/n1"),
    ("GET", "/api/nodes/label/L", "/api/goats/<goat>/nodes/label/L"),
    ("GET", "/api/relationships", "/api/goats/<goat>/relationships"),
    ("POST", "/api/relationships", "/api/goats/<goat>/relationships"),
    ("GET", "/api/relationships/r1", "/api/goats/<goat>/relationships/r1"),
    ("PATCH", "/api/relationships/r1", "/api/goats/<goat>/relationships/r1"),
    ("DELETE", "/api/relationships/r1", "/api/goats/<goat>/relationships/r1"),
    ("GET", "/api/graph", "/api/goats/<goat>/graph"),
    ("GET", "/api/operations", "/api/goats/<goat>/operations"),
    ("POST", "/api/operations", "/api/goats/<goat>/operations"),
    ("GET", "/api/operations/o1", "/api/goats/<goat>/operations/o1"),
    ("POST", "/api/operations/o1/results", "/api/goats/<goat>/operations/o1/results"),
    ("POST", "/api/operations/o1/validate", "/api/goats/<goat>/operations/o1/validate"),
    ("DELETE", "/api/operations/o1", "/api/goats/<goat>/operations/o1"),
]


@pytest.mark.parametrize("method,path,replacement", REMOVED)
def test_removed_route_returns_410_naming_replacement(env, client, method, path, replacement):
    # with a goat registered, so a 410 can't be mistaken for "nothing configured"
    env.create_goat("present", "memory")
    r = client.open(path, method=method, json={"name": "present", "nodeid": "n1"})
    assert r.status_code == 410
    body = r.get_json()
    assert body["api_version"] == 2
    assert body["error"].startswith("Removed in API v2 (ADR-016): ")
    assert replacement in body["error"]


def test_removed_routes_do_not_touch_any_goat(env, client):
    env.create_goat("untouched", "memory")
    client.post("/api/nodes", json={"nodeid": "leak"})
    client.post("/api/active-goat", json={"name": "untouched"})
    client.post("/api/backend", json={"type": "memory"})
    assert client.get("/api/goats/untouched/nodes").get_json() == []


# ----------------------------------------------------------------------
# POST /api/goats validation
# ----------------------------------------------------------------------

@pytest.mark.parametrize("field", ["make_active", "make_default"])
@pytest.mark.parametrize("value", [True, False])
def test_make_active_and_make_default_are_rejected(env, client, field, value):
    r = client.post("/api/goats", json={"name": "mk", "type": "memory", field: value})
    assert r.status_code == 400
    assert "make_active/make_default" in r.get_json()["error"]
    assert client.get("/api/goats").get_json()["goats"] == []


BAD_CREATE_NAMES = ["../x", "..", "a/b", "-x", "_x", "x" * 65, "é", "goat-é", "a b", "a.b",
                    ".hidden", 123]


@pytest.mark.parametrize("goat_type", ["memory", "text"])
@pytest.mark.parametrize("name", BAD_CREATE_NAMES)
def test_invalid_goat_names_are_rejected_on_create(env, client, name, goat_type):
    r = client.post("/api/goats", json={"name": name, "type": goat_type})
    assert r.status_code == 400
    assert "Invalid goat name" in r.get_json()["error"]
    assert client.get("/api/goats").get_json()["goats"] == []
    # nothing was created on disk next to or above the data dir
    assert os.listdir(env.data_dir) == []
    assert sorted(os.listdir(env.root)) == ["goats", "test_registry.json"]


@pytest.mark.parametrize("name", ["x\n", "goat\n"])
def test_goat_name_with_trailing_newline_is_rejected(client, name):
    r = client.post("/api/goats", json={"name": name, "type": "memory"})
    assert r.status_code == 400


def test_empty_and_missing_goat_names_are_rejected(client):
    for body in ({"name": "", "type": "memory"}, {"type": "memory"}, {"name": None, "type": "memory"}):
        r = client.post("/api/goats", json=body)
        assert r.status_code == 400
    assert client.get("/api/goats").get_json()["goats"] == []


@pytest.mark.parametrize("name", ["a", "9lives", "A_b-C9", "x" * 64, "xpal-test", "AVGFGoat"])
def test_valid_goat_names_are_accepted(client, name):
    assert re.match(mojogoatapi.GOAT_NAME_PATTERN, name)
    r = client.post("/api/goats", json={"name": name, "type": "memory"})
    assert r.status_code == 201
    assert client.get(f"/api/goats/{name}").get_json()["name"] == name
    assert client.get(f"/api/goats/{name}/nodes").status_code == 200


def test_duplicate_name_is_409(env, client):
    env.create_goat("dup", "memory")
    r = client.post("/api/goats", json={"name": "dup", "type": "memory"})
    assert r.status_code == 409


def test_derived_text_path_is_inside_data_dir(env, client):
    r = client.post("/api/goats", json={"name": "derived", "type": "text"})
    assert r.status_code == 201
    goatpath = r.get_json()["goat"]["goatpath"]
    assert goatpath == os.path.join(env.data_dir, "derived")
    assert os.path.commonpath([os.path.realpath(goatpath), os.path.realpath(env.data_dir)]) \
        == os.path.realpath(env.data_dir)
    assert os.path.isdir(goatpath)
    assert client.get("/api/goats/derived").get_json()["goatpath"] == goatpath


def test_derived_text_path_escaping_via_symlink_is_400(env, client):
    outside = env.path("outside")
    os.makedirs(outside)
    os.symlink(outside, os.path.join(env.data_dir, "evil"))
    r = client.post("/api/goats", json={"name": "evil", "type": "text"})
    assert r.status_code == 400
    assert "escapes" in r.get_json()["error"]
    assert os.listdir(outside) == []
    assert client.get("/api/goats").get_json()["goats"] == []


@pytest.mark.parametrize("bad_path", ["relative/path", "./here", "../up", "goats"])
def test_explicit_relative_goat_path_is_400(env, client, bad_path):
    r = client.post("/api/goats", json={"name": "rel", "type": "text", "goat_path": bad_path})
    assert r.status_code == 400
    assert "absolute" in r.get_json()["error"]
    assert client.get("/api/goats").get_json()["goats"] == []


def test_explicit_absolute_goat_path_outside_data_dir_is_allowed(env, client):
    elsewhere = env.path("elsewhere", "remote_goat")
    r = client.post("/api/goats", json={"name": "remote", "type": "text", "goat_path": elsewhere})
    assert r.status_code == 201
    assert r.get_json()["goat"]["goatpath"] == elsewhere
    assert os.path.isdir(elsewhere)


def test_unwritable_text_goat_path_is_400_at_create(env, client):
    # a path whose parent is a regular file fails for root and non-root alike
    afile = env.path("afile")
    with open(afile, "w") as f:
        f.write("not a directory")
    r = client.post("/api/goats", json={"name": "unwritable", "type": "text",
                                        "goat_path": os.path.join(afile, "sub")})
    assert r.status_code == 400
    assert "error" in r.get_json()
    # nothing registered, nothing cached, registry file untouched
    assert client.get("/api/goats").get_json()["goats"] == []
    assert "unwritable" not in mojogoatapi._goat_cache
    assert client.get("/api/goats/unwritable/nodes").status_code == 404


def test_text_goat_path_already_used_is_409(env, client):
    path = env.create_text_goat("first")
    r = client.post("/api/goats", json={"name": "second", "type": "text", "goat_path": path})
    assert r.status_code == 409


# ----------------------------------------------------------------------
# GET /api/goats/<name>, status, health
# ----------------------------------------------------------------------

def test_get_goat_returns_registry_entry_at_top_level(env, client):
    path = env.create_text_goat("entry")
    env.create_goat("entry_mem", "memory", description="d")
    r = client.get("/api/goats/entry")
    assert r.status_code == 200
    body = r.get_json()
    assert body["name"] == "entry" and body["type"] == "text"
    assert body["goatpath"] == path and body["goatname"] == "entry"
    assert "created" in body and "description" in body
    assert "goat" not in body  # entry is the top-level body, not wrapped
    mem = client.get("/api/goats/entry_mem").get_json()
    assert mem["type"] == "memory" and mem["description"] == "d"
    assert body in client.get("/api/goats").get_json()["goats"]


def test_get_goat_unknown_is_404(client):
    r = client.get("/api/goats/nope")
    assert r.status_code == 404
    assert r.get_json() == {"error": "Goat 'nope' not found"}


def test_status_reports_api_v2_and_no_active_goat_fields(env, client):
    env.create_text_goat("st1")
    env.create_goat("st2", "memory")
    body = client.get("/api/status").get_json()
    assert body["api_version"] == 2
    assert "active_goat" not in body
    assert [g["name"] for g in body["goats"]] == ["st1", "st2"]
    for g in body["goats"]:
        assert "is_active" not in g and "is_default" not in g
    for key in ("status", "config", "backends", "goats", "operations", "timestamp"):
        assert key in body
    paths = [o["path"] for o in body["operations"]]
    assert "/api/goats/<goat>/nodes" in paths and "/api/goats/<goat>/operations" in paths
    assert not any(p.startswith(("/api/nodes", "/api/active-goat", "/api/relationships",
                                 "/api/graph", "/api/backend")) for p in paths)


def test_health_has_no_active_goat(env, client):
    env.create_goat("h1", "memory")
    assert client.get("/health").get_json() == {"status": "ok", "goat_count": 1}


# ----------------------------------------------------------------------
# Registry file: legacy active/default
# ----------------------------------------------------------------------

def _legacy_registry(env):
    return {
        "goats": [{"name": "old_text", "type": "text", "goatname": "old_text",
                   "goatpath": env.path("old_text"), "created": "2026-01-01T00:00:00",
                   "description": "legacy"},
                  {"name": "old_mem", "type": "memory", "created": "2026-01-01T00:00:00"}],
        "active": "old_text",
        "default": "old_mem",
    }


def test_legacy_active_default_are_ignored_on_load_and_dropped_on_next_save(env, client):
    env.write_registry(_legacy_registry(env))

    listing = client.get("/api/goats").get_json()
    assert [g["name"] for g in listing["goats"]] == ["old_text", "old_mem"]
    assert "active" not in listing and "default" not in listing
    assert "active" not in mojogoatapi.registry and "default" not in mojogoatapi.registry
    # loading alone does not rewrite the file
    assert "active" in env.read_registry_file()

    # both goats work through scoped routes, and none is "the" goat
    assert client.get("/api/goats/old_text/nodes").status_code == 200
    assert client.post("/api/goats/old_mem/nodes", json={"nodeid": "n"}).status_code == 201
    assert client.get("/api/goats/old_text/nodes").get_json() == []

    # next save drops the fields
    env.create_goat("another", "memory")
    saved = env.read_registry_file()
    assert "active" not in saved and "default" not in saved
    assert [g["name"] for g in saved["goats"]] == ["old_text", "old_mem", "another"]


def test_post_registry_with_legacy_file_drops_fields_and_clears_goat_cache(env, client):
    env.create_goat("old_mem", "memory")
    assert client.post("/api/goats/old_mem/nodes", json={"nodeid": "n"}).status_code == 201
    assert "old_mem" in mojogoatapi._goat_cache

    other = env.path("other_registry.json")
    legacy = _legacy_registry(env)
    with open(other, "w") as f:
        json.dump(legacy, f)
    assert client.post("/api/registry", json={"path": other}).status_code == 200

    assert "active" not in mojogoatapi.registry and "default" not in mojogoatapi.registry
    assert mojogoatapi._goat_cache == {}
    # same name, new registry -> fresh empty memory goat
    assert client.get("/api/goats/old_mem/nodes").get_json() == []


# ----------------------------------------------------------------------
# Memory goats and the goat cache
# ----------------------------------------------------------------------

def test_memory_goat_summary_counts_after_writes(env, client):
    env.create_goat("memsum", "memory")
    s = client.get("/api/goats/memsum/summary").get_json()
    assert (s["node_count"], s["rel_count"], s["taxonomy"]) == (0, 0, {})
    assert "error" not in s

    for nodeid in ("a", "b", "c"):
        assert client.post("/api/goats/memsum/nodes", json={"nodeid": nodeid}).status_code == 201
    for target, story in (("b", "KNOWS"), ("c", "KNOWS"), ("c", "LIKES")):
        r = client.post("/api/goats/memsum/relationships",
                        json={"source": "a", "target": target, "story": story})
        assert r.status_code == 201

    s = client.get("/api/goats/memsum/summary").get_json()
    assert s["name"] == "memsum" and s["type"] == "memory"
    assert s["node_count"] == 3 and s["rel_count"] == 3
    assert s["taxonomy"] == {"KNOWS": 2, "LIKES": 1}


def test_memory_goat_state_persists_across_requests(env, client):
    env.create_goat("keep", "memory")
    client.post("/api/goats/keep/nodes", json={"nodeid": "n"})
    assert [n["nodeid"] for n in client.get("/api/goats/keep/nodes").get_json()] == ["n"]
    assert env.cached_goat("keep") is env.cached_goat("keep")


def test_goat_cache_is_per_name(env, client):
    env.create_goat("m1", "memory")
    env.create_goat("m2", "memory")
    client.post("/api/goats/m1/nodes", json={"nodeid": "only_m1"})
    assert env.cached_goat("m1") is not env.cached_goat("m2")
    assert client.get("/api/goats/m2/nodes").get_json() == []


def test_delete_goat_drops_cached_instance(env, client):
    env.create_goat("recycle", "memory")
    assert client.post("/api/goats/recycle/nodes", json={"nodeid": "n"}).status_code == 201
    first = env.cached_goat("recycle")
    assert "recycle" in mojogoatapi._goat_cache

    assert client.delete("/api/goats/recycle").status_code == 200
    assert "recycle" not in mojogoatapi._goat_cache
    assert client.get("/api/goats/recycle/nodes").status_code == 404

    env.create_goat("recycle", "memory")
    assert client.get("/api/goats/recycle/nodes").get_json() == []
    assert env.cached_goat("recycle") is not first


def test_delete_text_goat_drops_cached_instance_and_purge_removes_data(env, client):
    path = env.create_text_goat("txt_del")
    assert "txt_del" in mojogoatapi._goat_cache
    assert client.delete("/api/goats/txt_del?purge=true").status_code == 200
    assert "txt_del" not in mojogoatapi._goat_cache
    assert not os.path.exists(path)
    assert client.get("/api/goats/txt_del/nodes").status_code == 404


def test_delete_unknown_goat_is_404(client):
    assert client.delete("/api/goats/nope").status_code == 404


def test_goat_registered_but_unopenable_is_400_with_reason(env, client):
    afile = env.path("afile")
    with open(afile, "w") as f:
        f.write("x")
    env.write_registry({"goats": [{"name": "broken", "type": "text", "goatname": "broken",
                                   "goatpath": os.path.join(afile, "sub")}]})
    r = client.get("/api/goats/broken/nodes")
    assert r.status_code == 400
    assert "Failed to set up goat" in r.get_json()["error"]
    assert "broken" not in mojogoatapi._goat_cache


# ----------------------------------------------------------------------
# Operations scoped to a goat
# ----------------------------------------------------------------------

def _make_op(client, goat, name="op"):
    r = client.post(f"/api/goats/{goat}/operations", json={"name": name, "node_ids": [], "params": {}})
    assert r.status_code == 201
    return r.get_json()


def _post_result(client, goat, op_id, nodeid="z"):
    r = client.post(f"/api/goats/{goat}/operations/{op_id}/results", json={
        "results": [{"type": "add_node", "payload": {"nodeid": nodeid, "labels": ["New"]}}]})
    assert r.status_code == 200
    return r.get_json()["results"][0]["result_id"]


def test_operation_records_carry_their_goat(env, client):
    env.create_goat("opa", "memory")
    op = _make_op(client, "opa")
    assert op["goat"] == "opa"
    assert client.get(f"/api/goats/opa/operations/{op['operation_id']}").get_json()["goat"] == "opa"
    with open(os.path.join(env.operations_dir, f"{op['operation_id']}.json")) as f:
        assert json.load(f)["goat"] == "opa"


def test_list_operations_returns_only_own_goat(env, client):
    env.create_goat("opa", "memory")
    env.create_goat("opb", "memory")
    env.create_goat("opempty", "memory")
    a1, a2 = _make_op(client, "opa", "a1"), _make_op(client, "opa", "a2")
    b1 = _make_op(client, "opb", "b1")

    la = client.get("/api/goats/opa/operations")
    assert la.status_code == 200
    assert [o["operation_id"] for o in la.get_json()] == [a1["operation_id"], a2["operation_id"]]
    assert all(o["goat"] == "opa" for o in la.get_json())
    assert [o["operation_id"] for o in client.get("/api/goats/opb/operations").get_json()] \
        == [b1["operation_id"]]
    assert client.get("/api/goats/opempty/operations").get_json() == []


def test_operation_under_wrong_goat_is_404_for_get_results_validate_delete(env, client):
    env.create_goat("opa", "memory")
    env.create_goat("opb", "memory")
    op = _make_op(client, "opa")
    op_id = op["operation_id"]
    result_id = _post_result(client, "opa", op_id)

    wrong = f"/api/goats/opb/operations/{op_id}"
    assert client.get(wrong).status_code == 404
    assert client.post(f"{wrong}/results", json={"results": []}).status_code == 404
    assert client.post(f"{wrong}/validate",
                       json={"result_id": result_id, "action": "accept"}).status_code == 404
    assert client.delete(wrong).status_code == 404

    # nothing happened to it under its own goat
    own = client.get(f"/api/goats/opa/operations/{op_id}").get_json()
    assert own["status"] == "awaiting_validation"
    assert [r["status"] for r in own["results"]] == ["proposed"]
    assert os.path.exists(os.path.join(env.operations_dir, f"{op_id}.json"))


def test_validate_applies_accepted_write_to_the_urls_goat_only(env, client):
    env.create_goat("opa", "memory")
    env.create_goat("opb", "memory")
    op_id = _make_op(client, "opa")["operation_id"]
    result_id = _post_result(client, "opa", op_id, nodeid="only_in_a")

    # wrong goat first: refused, and no write anywhere
    r = client.post(f"/api/goats/opb/operations/{op_id}/validate",
                    json={"result_id": result_id, "action": "accept"})
    assert r.status_code == 404
    assert client.get("/api/goats/opa/nodes/only_in_a").status_code == 404
    assert client.get("/api/goats/opb/nodes/only_in_a").status_code == 404

    r = client.post(f"/api/goats/opa/operations/{op_id}/validate",
                    json={"result_id": result_id, "action": "accept"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "completed"
    assert client.get("/api/goats/opa/nodes/only_in_a").get_json()["labels"] == ["New"]
    assert client.get("/api/goats/opb/nodes/only_in_a").status_code == 404
    assert client.get("/api/goats/opb/nodes").get_json() == []


def test_unknown_goat_cannot_create_operations(client):
    r = client.post("/api/goats/ghost/operations", json={"name": "x"})
    assert r.status_code == 404
    assert operations.list_operations() == []


def test_operation_reload_skips_files_without_goat_and_leaves_them(env, client):
    env.create_goat("opa", "memory")
    env.create_goat("opb", "memory")
    op_id = _make_op(client, "opa")["operation_id"]
    _post_result(client, "opa", op_id)

    legacy_path = os.path.join(env.operations_dir, "legacy-no-goat.json")
    legacy = {"operation_id": "legacy-no-goat", "name": "old", "status": "awaiting_validation",
              "node_ids": [], "params": {},
              "results": [{"result_id": "r1", "status": "proposed", "type": "add_node",
                           "payload": {"nodeid": "legacy_node"}}],
              "created": "2026-01-01T00:00:00", "updated": "2026-01-01T00:00:00"}
    with open(legacy_path, "w") as f:
        json.dump(legacy, f)
    with open(legacy_path, "rb") as f:
        legacy_bytes = f.read()

    operations.reset_store()  # simulated restart
    assert operations.load_persisted() == 1

    assert client.get(f"/api/goats/opa/operations/{op_id}").status_code == 200
    assert client.get(f"/api/goats/opb/operations/{op_id}").status_code == 404
    for goat in ("opa", "opb"):
        assert client.get(f"/api/goats/{goat}/operations/legacy-no-goat").status_code == 404
        ids = [o["operation_id"] for o in client.get(f"/api/goats/{goat}/operations").get_json()]
        assert "legacy-no-goat" not in ids
    with open(legacy_path, "rb") as f:
        assert f.read() == legacy_bytes
