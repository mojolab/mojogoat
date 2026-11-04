# MojoGOAT — Open Tasks

## v0.4.0 — Goat-scoped API (BREAKING) — IN PLANNING (2026-10-31)

Removes the "active goat" entirely. Every goat-level route becomes `/api/goats/<goat>/…`.
Design: `docs/decisions/ADR-016-goat-scoped-api-remove-active-goat.md`; route spec:
`docs/api-v2-goat-scoped.md`. Issues: ISSUE-18 to ISSUE-21 in `tasks/pending-issues.md`.
Test client: Xetrapal (`/xpal-src/arjunvenkatraman/xetrapal3`, its ADR-028 and
`docs/two-xetrapals-ollama-test.md`). Editing the sibling repo is authorised for this work only
(user instruction, 2026-10-31).

Decisions already made (do not reopen without a new ADR):
- Everything is per goat, including operations. No compatibility mode, no fallback.
- Old routes return `410 Gone` with the replacement named; `/api/status` reports `api_version: 2`.
- Registry `active` and `default` fields are removed; `make_active`/`make_default` → 400.

Prerequisites
- [x] Branch `feat/goat-scoped-routes`. Commit or stash the existing uncommitted work first
      (4 real file changes plus 15 mode-only changes — check shebangs before trusting the
      mode-only diffs).
- [ ] Merge or rebase against `docs/adr-0015-and-samples` if it lands first (ADR-0015 numbering,
      ISSUE-12..17 numbering).

Server (`mojogoatapi.py`, `mojogoat/routes.py`, `mojogoat/operations.py`)
- [x] Goat cache + `resolve_goat(name)`; clear on `DELETE /api/goats/<name>` and `POST /api/registry`
- [x] `init_routes(app, resolve_goat)`; delete `set_active_goat_ref`, `get_active_goat`,
      `requires_active_goat`, the `import mojogoatapi` dependency and the `active_goat` globals
- [x] Move all data routes under `/api/goats/<goat>/…` (nodes, relationships, graph, composition,
      taxonomy, dump/import-relationships, compact, operations)
- [x] Add `GET /api/goats/<name>`
- [x] Operations: `goat` field on records; list/get scoped; skip pre-existing persisted files
      without `goat` (warn, leave on disk)
- [x] 410 stubs for removed routes; remove `/api/backend`, `/api/direct/nodes`, `/api/debug`
- [x] Drop registry `active`/`default`; reject `make_active`/`make_default`
- [x] Goat-name validation (ADR-016 §8): pattern on create and on every `<goat>` path segment;
      derived text path must resolve inside `DEFAULT_DATA_DIR`; explicit `goat_path` must be
      absolute; startup warning for non-matching registry names; tests including `../x`
- [x] `/api/status`: add `api_version: 2`, drop active/default fields; `/health`: drop `active_goat`

Tests (`tests/`)
- [x] Two text goats in temp dirs: interleaved writes stay isolated
- [x] Unknown goat → 404; scoped route never changes any server-wide state
- [x] Each removed route → 410 with replacement named
- [x] Operations scoped to goat (wrong-goat access → 404; legacy persisted file skipped)
- [x] Update `test_api.py`, `test_api_crud.py`, `test_api_cli.py`, `run_*` scripts, Postman collection
- [x] `uv run --extra dev pytest tests/ -m "not integration"` green (baseline 2026-10-31:
      128 passed, 2 skipped, 3 deselected)

Docs
- [x] `API_README.md` rewritten for v2 (kept `docs/api-v2-goat-scoped.md` as the normative spec
      rather than deleting it: the ADR, CLAUDE.md, todo and docs/README link to it)
- [x] Update `API_TEST_README.md` (also fix the stale `/xpal-src/mojogoat/test` paths)
- [x] Update `CLAUDE.md` "API Model" status line once the suite is green and the e2e run is done
- [x] `docs/README.md` ADR range

Concurrency — one Danav per goat, several Danavs at once  *(found 2026-11-04)*
- [x] Reproduced: 2 goats × 1 writer each was fine, but several concurrent writers on one goat
      stored 1 of 60 relationships, returned spurious 400s and stalled (HTTP timeouts). Cause:
      `TextGoat._REL_WRITE_LOCKS` held `asyncio.Lock`s, but Flask runs each request on its own
      thread/event loop, and an `asyncio.Lock` is bound to one loop (waiters released from another
      loop are never woken). The pointer file `goatrels.gq` was also truncated in place.
- [x] `textgoat.py`: per-goatpath `threading.Lock` (no `await` inside the critical section, so it
      cannot deadlock coroutines on one loop); relationship read-modify-write, `compact()` and
      `add_rels()` all run under it; pointer, snapshot and node files written atomically
      (temp file + `os.replace`); readers retry once if a compaction removes their snapshot;
      swallowed exceptions in create/delete/update now `logger.exception`
- [x] `tests/test_textgoat_concurrency.py` (6 tests): same-goat writers, two goats isolated,
      readers never see the graph shrink, same-loop `asyncio.gather`, compact during writes, and
      two goats over HTTP. On the old code 5 of 6 fail or hang; all pass now.
- [x] Cross-repo check against a live server: Xetrapal's `tests/integration/test_mojogoat_api.py`
      (7 passed) and two Xetrapal `MojoGoatSmritiGraph` clients in separate processes (40 writes
      each, 8 in flight, half confirmed): 40/40 stored, 20 pending each, no cross-goat records
      via the API or on disk, no server errors
- [ ] Not covered: `add_node` upserts of the *same* node from two clients are last-writer-wins
      (writes are atomic, merges are not); FalkorGoat/Neo4jGoat concurrency (their drivers own it)
- [ ] Known unrelated bug: `TextGoat.feed_goat` uses `uuid4` but never imports it (NameError)

Release
- [x] Tag v0.4.0 (breaking) — tagged locally 2026-11-04, **not pushed**
- [ ] Release notes: minimum versions — Xetrapal `feat/goat-scoped-client` or later; `mojogoat-ui` must use `/api/goats/<goat>/…` routes
- [ ] Push `feat/goat-scoped-routes` and tag `v0.4.0` (needs your go-ahead; v0.2.0 is also still unpushed)

---

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
