# MojoGOAT — Open Tasks

## v0.2.0 — COMPLETE

All items done (2026-02-24 to 2026-03-15). See git log for details.
Tag created locally; `git push origin v0.2.0` pending GitLab auth.

---

# v0.3.0 — COMPLETE

All items (11–17) implemented and tested as of 2026-06-11. Suite green: 148 passed,
6 integration deselected. Plan retained below for reference.

| Item | Description | Status |
|------|-------------|--------|
| 11 | Backend hierarchy: Neo4j primary, FalkorDB opt-in (ADR-010) | done |
| 12 | `GET /api/graph` endpoint (ADR-011) | done |
| 13 | Operations API (ADR-012) | done |
| 14 | TextGoat snapshot compaction (ADR-007) | done |
| 15 | Bulk import (inverse of dump) | done |
| 16 | API test coverage gaps | done |
| 17 | Graph workbench UI (ADR-013, separate repo) | done |

---

# v0.3.0 Plan (reference)

## Item 11 — Backend hierarchy: Neo4j primary, FalkorDB opt-in (ADR-010)

Remove FalkorDB from `auto` backend selection. Auto order becomes `text → memory` only.
Neo4j and FalkorDB both require explicit `type:` configuration.

**Files:** `mojogoatapi.py` (`_select_backend`, `GET /api/status` descriptions)
**Tests:** verify `auto` does not probe FalkorDB or Neo4j

---

## Item 12 — `GET /api/graph` endpoint (ADR-011)

Returns `{nodes, edges, node_count, edge_count}` from the active goat.
Filters: `source`, `target`, `story`, `limit`, `node_ids` (comma-separated), extra params → props filter.
Node inclusion rule: only nodes referenced by at least one returned edge (or explicitly in `node_ids`).

**Files:** `mojogoat/routes.py`
**Tests:** `test_api.py` — graph endpoint with and without filters

---

## Item 13 — Operations API (ADR-012)

In-memory operation store on the API process. Endpoints:
- `POST   /api/operations`
- `GET    /api/operations/<id>`
- `POST   /api/operations/<id>/results`
- `POST   /api/operations/<id>/validate`
- `DELETE /api/operations/<id>`

External processes poll for operations and post results. Human validates via the workbench.
Accepted results are written to the active goat via normal create/update calls.

**Files:** `mojogoat/routes.py` (or new `mojogoat/operations.py`)
**Tests:** full unit test suite covering all status transitions

---

## Item 14 — TextGoat snapshot compaction (ADR-007)

TextGoat appends to flat files unboundedly. Implement compaction: rewrite the current
state to a new snapshot file, archive the old append log.

**Files:** `mojogoat/goatbases/textgoat.py`
**API:** `POST /api/active-goat/compact` (text goats only; 400 for other types)
**Tests:** verify relationship count unchanged after compaction; verify old log is archived

---

## Item 15 — Bulk import (inverse of dump)

`POST /api/active-goat/import-relationships` — accepts a pipe-delimited quad file
(same format as `dump-relationships`) and writes each line as a new relationship.
Returns `{imported: N, skipped: N, errors: [...]}`.

**Files:** `mojogoat/routes.py`, each backend's `create_relationship`
**Tests:** round-trip: dump → wipe → import → verify count and content

---

## Item 16 — API test coverage gaps

Missing tests in `test_api.py`:
- `PATCH /api/relationships/<id>` updates props and returns 200
- `DELETE /api/goats/<name>?purge=true` removes registry entry
- `GET /api/goats/<name>/summary` returns node/rel/taxonomy counts
- `POST /api/backend` auto-selects text when FalkorDB absent

---

## Item 17 — Graph workbench UI (ADR-013)

Separate repository (`mojogoat-ui`). React + Cytoscape.js. Pure API consumer.

**Panels:** canvas, inspector, filter bar, layout switcher, operations panel, validation queue
**Depends on:** Items 12 and 13 (graph API + operations API)
**Scope:** This is a separate repo — create it and scaffold the project structure.

---

## Ordering

11 → 12 → 13 (unblocks workbench) → 16 (test gaps, any order) → 14 → 15 → 17 (workbench, last)
