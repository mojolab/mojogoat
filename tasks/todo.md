# MojoGOAT — Open Tasks

## Item 1 — Tag v0.2.0

All Phase 1 tasks are complete:
- [x] TextGoat async rewrite + 20 pytest tests
- [x] Neo4jGoat async rewrite + pytest suite (29 unit + 3 integration)
- [x] FalkorGoat implementation + 25 unit + 3 integration tests
- [x] neo4jgoat.py (py2neo) retired
- [x] pyproject.toml cleaned up (legacy group removed)
- [x] Architecture.md rewritten
- [x] docs/adr/ with 5 ADRs
- [x] CLAUDE.md roadmap checkboxes updated

**Action:** ~~`git tag v0.2.0`~~ Done locally (2026-02-24). pyproject.toml comment updated to correct GitLab URL.
**Pending:** `git push origin v0.2.0` — needs GitLab auth (no credentials in dev container).

---

## Item 2 — SmritiGraph adapter — SUPERSEDED

~~FalkorDBSmritiGraph as a Python library wrapper~~ — architecture changed (2026-02-24).

Xetrapal now uses `MojoGoatSmritiGraph`, an HTTP client to the MojoGOAT REST API
(`xetrapal/smriti/mojogoat.py`). Xetrapal does not import FalkorGoat directly.
All graph operations go through `http://localhost:5000`.

**No action needed on MojoGOAT side** — just ensure Items 6 and 7 are resolved so
Xetrapal gets full confirm/invalidate persistence and FalkorDB as the backend.

---

## Item 3 — Add `get_relationship(relationship_id)` to GoatBase + FalkorGoat ✅

Done 2026-02-24. Added to GoatBase (abstract), FalkorGoat, TextGoat, Neo4jGoat.
Tests added to test_falkorgoat_async.py and test_textgoat_async.py.

---

## Item 4 — Add `props` filter + `limit` to `get_relationships()` ✅

Done 2026-02-24. Added `props: dict | None` and `limit: int | None` to GoatBase,
FalkorGoat (Cypher WHERE + LIMIT), TextGoat (post-filter + early break), Neo4jGoat.
Tests added to test_falkorgoat_async.py and test_textgoat_async.py.

---

## Item 5 — Bump pyproject.toml version to 0.2.0 ✅

Done 2026-02-24. pyproject.toml now reads `version = "0.2.0"`.

---

## Item 6 — Add `PATCH /api/relationships/<id>` for property updates ✅

**Found during:** Xetrapal MojoGoatSmritiGraph integration (2026-02-24).

`POST /api/relationships` and `DELETE /api/relationships/<id>` exist, but there is no
way to update a relationship's properties in-place. Xetrapal needs this to implement
`SmritiGraph.confirm()` and `SmritiGraph.invalidate()` — both transition the
`smriti_state` property on an existing relationship.

Without this, Xetrapal falls back to an in-memory state overlay (lost on restart).

**Required addition to `mojogoatapi.py`:**
```python
@app.route('/api/relationships/<relationship_id>', methods=['PATCH'])
def update_relationship(relationship_id):
    """Update properties on an existing relationship."""
    data = request.json or {}
    success = asyncio.run(active_goat.update_relationship_props(relationship_id, **data))
    if not success:
        return jsonify({"error": "Relationship not found"}), 404
    return jsonify({"message": "Updated", "relationship_id": relationship_id})
```

Tests: add `test_patch_relationship_updates_state` to test suite.
Xetrapal integration test: `tests/integration/test_mojogoat_api.py::test_item6_patch_relationship`

---

## Item 7 — Add FalkorDB backend support to REST API ✅

**Found during:** Xetrapal setup (2026-02-24).

`POST /api/goats` only handles `type: "text"` and `type: "neo4j"`. FalkorDB is supported
in the Python library (`FalkorGoat`) but not exposed via the REST API.

**Required addition to `mojogoatapi.py`** (in `create_goat()` and `set_active_goat()`):
```python
elif data.get("type") == "falkordb":
    goat_config["host"] = data.get("host", "localhost")
    goat_config["port"] = int(data.get("port", 6379))
    goat_config["graph_name"] = data.get("graph_name", "mojogoat")
    # In set_active_goat():
    from mojogoat.goatbases.falkorgoat import FalkorGoat
    active_goat = FalkorGoat(
        host=goat_config["host"],
        port=goat_config["port"],
        graph_name=goat_config.get("graph_name", "mojogoat"),
    )
```

Tests: add `test_create_falkordb_goat` (integration, requires FalkorDB on :6379).
Xetrapal integration test: `tests/integration/test_mojogoat_api.py::test_item7_falkordb_backend`

**Design goal:** Once Item 7 is done, callers (Xetrapal) should only need to know the
`goat_name` — FalkorDB host/port/graph_name should live in MojoGOAT's own registry
config, not in the caller's config file. The caller should not need to know or care
what backend is behind a named goat.

---

## Item 8 — Add `GET /health` endpoint ✅

**Found during:** Xetrapal ADR 018 (management REPL), 2026-02-24.

`ManagementClient.ping()` currently uses `GET /api/goats` as a proxy for liveness, which
is fragile — it returns 500 on DB error even if the server is up. A dedicated health
endpoint is needed.

**Required addition to `mojogoatapi.py`:**
```python
@app.route('/health', methods=['GET'])
def health():
    """Liveness check — returns 200 if the server is running."""
    return jsonify({
        "status": "ok",
        "goat_count": len(goats),         # number of registered goats
        "active_goat": active_goat.name if active_goat else None,
    })
```

**Xetrapal usage:** `ManagementClient.ping()` should switch to `GET /health` once this
lands. Until then it falls back to `GET /api/goats`.

Tests: `GET /health → {"status": "ok"}` with status 200.

---

## Item 9 — Verify/add `?target=<uri>` filter in `GET /api/relationships` ✅

**Found during:** Xetrapal ADR 018 (management REPL — "list jeevas"), 2026-02-24.

Xetrapal needs to query: "give me all Smritis where target is `type:jeeva` and story is
`is a`" to list all registered Jeevas without client-side filtering.

**Required test:**
```
GET /api/relationships?target=type:jeeva&story=is+a&smriti_state=confirmed
```

If the `target` filter is not yet supported in `get_relationships()`, add it alongside
the existing `source` filter (Item 4 added `source` and `story` filters).

**Xetrapal workaround** (until this lands): `ManagementClient` fetches all relationships
with `story=is+a&smriti_state=confirmed` and filters `target == "type:jeeva"` in Python.
This is acceptable for small registries but will not scale.

Tests: add `test_filter_by_target` to test_textgoat_async.py and test_falkorgoat_async.py.

---

## Item 10 — `POST /api/nodes` returns 500 for node IDs containing slashes ✅

**Found during:** Xetrapal `create jeeva` command (2026-02-25).

When a `nodeid` contains literal slash characters (e.g. `val:/xpal-data/xpals/xpal1`),
`POST /api/nodes` returns 500 instead of a descriptive 400. The caller (Xetrapal) sees
`add_node returned 500` in a log warning, then gets a 400 on the subsequent relationship
write because the node was never created.

**Root cause:** Slashes in the `nodeid` JSON field likely collide with internal URL routing
or path handling in TextGoat's file-based storage (the node ID is used as a filename or
dict key that breaks on `/`).

**Fix:** `POST /api/nodes` should validate `nodeid` and return `400 Bad Request` with a
clear message if the ID contains characters that cannot be stored. Alternatively, percent-
encode the nodeid internally before use in storage.

**Xetrapal fix applied:** `prefixes.literal()` now uses `urllib.parse.quote(safe='')` so
literal values (paths, URLs, etc.) are always percent-encoded before becoming `val:` URIs
(e.g. `val:%2Fxpal-data%2Fxpals%2Fxpal1`). MojoGOAT never receives a raw slash in a URI.

**Remaining MojoGOAT action:** Harden `POST /api/nodes` to return 400 with a useful
message instead of 500 when the nodeid is malformed, so callers get actionable errors.

Tests: `test_post_node_with_slash_returns_400` in test_mojogoatapi.py.
