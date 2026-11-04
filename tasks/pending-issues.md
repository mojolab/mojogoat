# Pending Issues — MojoGOAT

Generated 2026-06-19. File these at https://gitlab.com/mojolab/mojogoat/-/issues/new
(or via `glab issue create` once authenticated).

Priority order: P0 → P1 → P2 → P3.

---

## P0 — Unblock / Must-do before next integration

---

### ISSUE-1 · [task] Push v0.2.0 tag to GitLab

**Labels:** task, release  
**Milestone:** v0.2.0

**Goal:**  
`git push origin v0.2.0` is pending GitLab auth. Once auth is resolved, push the tag so Xetrapal can pin to it.

**Acceptance criteria:**
- [ ] `git ls-remote --tags origin` shows `refs/tags/v0.2.0`
- [ ] GitLab Releases page shows v0.2.0 entry
- [ ] Xetrapal's `pyproject.toml` updated to `mojogoat = { git = "...", tag = "v0.2.0" }`

**Files affected:** none (git operation only; Xetrapal `pyproject.toml` is a sibling repo change)

**Blocked by:** GitLab auth in this environment

---

### ISSUE-2 · [task] Tag and publish v0.3.0 release

**Labels:** task, release  
**Milestone:** v0.3.0

**Goal:**  
All v0.3.0 items (11–17) are complete and suite is green (148 passed). Tag the commit and create a GitLab release entry.

**Acceptance criteria:**
- [ ] `git tag v0.3.0 <commit>` on the commit where suite reached 148 passed
- [ ] `git push origin v0.3.0`
- [ ] GitLab release notes summarise Items 11–17 (backend hierarchy, graph API, operations API, compaction, bulk import, test coverage, workbench UI)

**Blocked by:** ISSUE-1 (do v0.2.0 first)

---

## P1 — Next sprint (v0.4.0 foundations)

---

### ISSUE-3 · [feature] MongogoatModels backend

**Labels:** enhancement, backend  
**Milestone:** v0.4.0

**What and why:**  
The MongogoatModels backend (MongoDB + Postgres) has been deferred since the project started. With TextGoat, Neo4jGoat, FalkorGoat, and MemoryGoat stable, this is the remaining backend gap. Required for deployments that cannot run a dedicated graph database.

**Proposed interface:**  
Drop-in replacement implementing the same async interface as `textgoat.py` and `newneo4jgoatcopilot.py`. Constructor accepts `mongo_uri`, `db_name`, `pg_dsn`.

**Affected backends:** MongogoatModels only  
**Quad model impact:** No — storage format change only; quad contract unchanged

**Acceptance criteria:**
- [ ] `mojogoat/goatbases/mongogoat/` implementation complete
- [ ] Same test scenarios as `test_textgoat_async.py` pass against a live Mongo instance
- [ ] Integration tests gated with `@pytest.mark.integration`
- [ ] ADR-014 written documenting the storage schema

**Blocked by:** ISSUE-2 (v0.3.0 stable baseline)

---

### ISSUE-4 · [feature] OpenAPI / Swagger spec for mojogoatapi.py

**Labels:** enhancement, documentation  
**Milestone:** v0.4.0

**What and why:**  
The REST API has 13+ endpoints with no machine-readable spec. The mojogoat-ui and any future API consumers (Xetrapal HTTP mode, external tools) would benefit from a spec for client generation and interactive docs.

**Proposed interface:**  
`GET /api/openapi.json` returns the OpenAPI 3.1 spec. `GET /api/docs` serves Swagger UI.  
Generated via `flask-smorest` or hand-authored YAML — whichever creates less maintenance overhead.

**Affected backends:** API layer only  
**Quad model impact:** No

**Acceptance criteria:**
- [ ] All endpoints in MEMORY.md API Surface section covered in spec
- [ ] `GET /api/openapi.json` returns valid OpenAPI 3.1 JSON
- [ ] Request/response schemas match actual behaviour
- [ ] No changes to existing endpoint behaviour

---

### ISSUE-5 · [task] mojogoat-ui: wire Operations panel to live API

**Labels:** task, ui  
**Milestone:** v0.4.0  
**Repo:** mojogoat-ui (file there, not here)

**Goal:**  
The mojogoat-ui workbench was scaffolded in v0.3.0 (Item 17, ADR-013). The Operations panel and validation queue need to poll `GET /api/operations/<id>` and call `POST /api/operations/<id>/validate`. Currently the panel is likely a stub.

**Acceptance criteria:**
- [ ] Operations panel lists all pending operations from `GET /api/operations`
- [ ] Clicking an operation shows its current state and result (if any)
- [ ] Validate / reject buttons call `POST /api/operations/<id>/validate`
- [ ] Panel auto-refreshes on a configurable interval (default 5s)
- [ ] No polling when panel is not visible

**Blocked by:** ISSUE-2 (v0.3.0 tag — confirms operations API is stable)

---

### ISSUE-6 · [task] mojogoat-ui: Cytoscape.js canvas wired to /api/graph filters

**Labels:** task, ui  
**Repo:** mojogoat-ui (file there, not here)

**Goal:**  
`GET /api/graph` supports `source`, `target`, `story`, `limit`, `node_ids` filters (ADR-011). The filter bar in the workbench should drive these query params and re-render the canvas on change.

**Acceptance criteria:**
- [ ] Filter bar fields map 1:1 to `/api/graph` query params
- [ ] Changing a filter re-fetches and re-renders without full page reload
- [ ] Empty filter state fetches unfiltered graph (respects `limit` default)
- [ ] Node count and edge count displayed from API response

---

## P2 — Near-term quality / operability

---

### ISSUE-7 · [task] API authentication middleware

**Labels:** task, security  
**Milestone:** v0.4.0

**Goal:**  
`mojogoatapi.py` currently has no authentication. Any process that can reach port 5000 can read or write any goat. Add token-based auth (static bearer token from env var) as a minimum viable gate.

**Acceptance criteria:**
- [ ] All write endpoints (`POST`, `PATCH`, `DELETE`) require `Authorization: Bearer <token>`
- [ ] Token loaded from `MOJOGOAT_API_TOKEN` env var; missing env var disables auth (dev mode, logged as warning)
- [ ] `GET /health` remains unauthenticated
- [ ] `GET` read endpoints configurable to require auth (env var flag)
- [ ] 401 response on missing/invalid token with `WWW-Authenticate: Bearer` header
- [ ] Tests updated to pass token in headers

---

### ISSUE-8 · [task] Benchmark suite: TextGoat vs MemoryGoat vs Neo4jGoat at scale

**Labels:** task, performance  
**Milestone:** v0.4.0

**Goal:**  
No performance baseline exists. A benchmark suite (not a pytest suite — a standalone script) that creates 1k / 10k / 100k relationships and measures `create_relationship`, `get_relationships` (full scan), and `get_relationships` (filtered by story) across backends.

**Acceptance criteria:**
- [ ] `tools/benchmark.py` runnable with `uv run python tools/benchmark.py --backend text --count 10000`
- [ ] Outputs wall time and ops/sec for each operation
- [ ] Results written to `tools/benchmark-results/` as CSV
- [ ] Integration-gated (requires live backend for Neo4j)

---

### ISSUE-9 · [feature] Server-Sent Events for operations API

**Labels:** enhancement  
**Milestone:** future

**What and why:**  
The mojogoat-ui polls `GET /api/operations` on a timer. SSE would let the server push operation state changes, reducing latency and unnecessary requests. Makes sense once the operations API is heavily used.

**Proposed interface:**  
`GET /api/operations/stream` — SSE endpoint that emits an event whenever an operation changes state.

**Quad model impact:** No  
**Affected backends:** API layer only

**Acceptance criteria:**
- [ ] SSE endpoint emits `data: {id, status, updated_at}` on each state transition
- [ ] mojogoat-ui switches from polling to SSE with polling as fallback
- [ ] ADR-015 written

**Blocked by:** ISSUE-5 (polling must work first)

---

## P3 — Future / deferred

---

### ISSUE-10 · [feature] Multi-goat relationship query

**Labels:** enhancement, future

**What and why:**  
All queries are scoped to a single goat (to the active goat today; to the goat in the URL after ADR-016 / ISSUE-18, which removes the active goat). Some use cases (e.g. Xetrapal cross-graph reasoning) need to join relationships across two goats in one call. After ADR-016 a client can already make two scoped calls and merge them; this issue is about a server-side merged query.

**Proposed interface:**  
`GET /api/graph?goats=goat1,goat2` — returns merged nodes/edges from multiple goats.  
Or a dedicated `POST /api/query` with a goat list in the body.

**ADR needed:** Yes — this touches the goat isolation model.

**Blocked by:** MongogoatModels stable (ISSUE-3), ops experience with multi-goat patterns

---

### ISSUE-11 · [task] ADR index page

**Labels:** documentation

**Goal:**  
`docs/decisions/` has 13 ADRs with no index. A `docs/decisions/README.md` listing each ADR by number, title, and one-line summary makes the decision log navigable without reading every file.

**Acceptance criteria:**
- [ ] `docs/decisions/README.md` lists ADR-001 through ADR-013 (and future ones as added)
- [ ] Each row: number | title | status | one-line summary

---

## Goat-scoped API (ADR-016) — added 2026-10-31

Numbered from 18 because ISSUE-12..17 are already used on the unmerged branch
`docs/adr-0015-and-samples`.

---

### ISSUE-18 · [feature] Goat-scoped API; remove the active goat

**Labels:** feature, breaking, api
**Milestone:** v0.4.0

**Goal:**
Implement ADR-016. All data routes live under `/api/goats/<goat>/…`; `/api/active-goat*`,
`/api/backend`, `/api/direct/nodes`, `/api/debug` and the unscoped data routes are removed
(410 stubs this release).

**Acceptance criteria:**
- [ ] Routes and behaviour match `docs/api-v2-goat-scoped.md`
- [ ] No module-level `active_goat`; `routes.py` receives a resolver via `init_routes`
- [ ] `/api/status` reports `api_version: 2`
- [ ] Operations are scoped per goat
- [ ] Goat names validated (ADR-016 §8): `../x`, empty, over-long and non-ASCII names rejected on
      create; derived text paths cannot escape `DEFAULT_DATA_DIR`
- [ ] Two interleaved clients on two goats stay isolated (test)
- [ ] Suite green with `-m "not integration"`

**Files affected:** `mojogoatapi.py`, `mojogoat/routes.py`, `mojogoat/operations.py`, tests
**ADR:** ADR-016
**Blocked by:** nothing

---

### ISSUE-19 · [task] mojogoat-ui: migrate off the active-goat API

**Labels:** task, ui, breaking
**Milestone:** v0.4.0

**Goal:**
`mojogoat-ui` (separate repo) calls `/api/active-goat`, `/api/active-goat/taxonomy`, `/api/graph`,
`/api/nodes`, `/api/relationships` and `/api/operations` (`src/api/client.js`). All of these stop
working with ISSUE-18. The UI needs a goat selector (it already lists goats via `/api/goats`) and
must send the chosen goat name on every call. Not started; this repo does not modify the UI.

**Acceptance criteria:**
- [ ] UI picks a goat from `GET /api/goats` and scopes every request to it
- [ ] UI checks `api_version >= 2` from `/api/status` and shows a clear message otherwise
- [ ] ISSUE-5 and ISSUE-6 are built against the scoped routes, not the old ones

**Blocked by:** ISSUE-18 route spec (not its implementation)

---

### ISSUE-20 · [task] Update tests, Postman, CLI scripts and docs for scoped routes

**Labels:** task, documentation, tests
**Milestone:** v0.4.0

**Goal:**
Everything that calls the old routes is updated: `tests/test_api.py`, `tests/test_api_crud.py`,
`tests/test_api_cli.py`, `tests/run_api_tests.py`, `tests/run_api_cli_tests.sh`,
`tests/run_all_tests.sh`, `postman/*.json`, `samples/` (if present), `API_README.md`,
`API_TEST_README.md`, `goatctl.sh`, `goatwatch.py`, `mojogoatsync.py`.

**Acceptance criteria:**
- [ ] No remaining reference to `/api/active-goat` or an unscoped data route (`grep` clean)
- [ ] `API_TEST_README.md` paths corrected (`/xpal-src/mojogoat/test` is stale)
- [ ] Postman collection runs green against a v0.4.0 server

**Blocked by:** ISSUE-18

---

### ISSUE-21 · [bug] Concurrent relationship writes to one text goat fail or hang

**Labels:** bug, concurrency
**Milestone:** future

**Evidence (2026-11-01, pre-existing — identical on committed v1 `e1ed213` and on v2):**
Raw HTTP, nodes pre-created, N concurrent `POST …/relationships` to ONE text goat:
N=3 → `{201: 1, 400: 1, timeout: 1}`; N=12 → `{201: 1, 400: 10, timeout: 1}` (8 s client timeout,
error bodies not captured). Only 1 relationship stored in each case. Concurrent
`POST …/nodes` (N=12, distinct ids) all returned `201`. Two goats written concurrently also
failed within each goat, so this is per-goat, not cross-goat interference.

**Goal:**
`TextGoat._REL_WRITE_LOCKS` are `asyncio.Lock`s keyed by `goatpath`, and Flask runs each async view
on its own event loop, so one suspected cause is that the lock does not serialise requests across
loops. Not verified. Not hit by one-writer-per-goat deployments that write sequentially (ADR-016
§7; Xetrapal writes sequentially), but any multi-writer or parallel-writing client loses data or
hangs.

**Acceptance criteria:**
- [ ] Test with N concurrent writers to one text goat; no lost or corrupted relationships
- [ ] Fix, or document, the single-writer-per-goat constraint

---

## Priority summary

| Issue | Title | Priority | Milestone |
|-------|-------|----------|-----------|
| ISSUE-1 | Push v0.2.0 tag | P0 | v0.2.0 |
| ISSUE-2 | Tag and publish v0.3.0 | P0 | v0.3.0 |
| ISSUE-3 | MongogoatModels backend | P1 | v0.4.0 |
| ISSUE-4 | OpenAPI spec | P1 | v0.4.0 |
| ISSUE-5 | UI: Operations panel wired | P1 | v0.4.0 |
| ISSUE-6 | UI: Graph filter bar wired | P1 | v0.4.0 |
| ISSUE-7 | API auth middleware | P2 | v0.4.0 |
| ISSUE-8 | Benchmark suite | P2 | v0.4.0 |
| ISSUE-9 | SSE for operations API | P2 | future |
| ISSUE-10 | Multi-goat query | P3 | future |
| ISSUE-11 | ADR index | P3 | anytime |
| ISSUE-18 | Goat-scoped API; remove active goat (ADR-016) | P0 | v0.4.0 |
| ISSUE-19 | mojogoat-ui: migrate off active-goat API | P1 | v0.4.0 |
| ISSUE-20 | Update tests/Postman/scripts/docs for scoped routes | P1 | v0.4.0 |
| ISSUE-21 | Concurrent relationship writes to one text goat fail/hang (pre-existing) | P1 | future |
