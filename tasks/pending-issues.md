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
- [ ] ADR-0014 written documenting the storage schema

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
The mojogoat-ui workbench was scaffolded in v0.3.0 (Item 17, ADR-0013). The Operations panel and validation queue need to poll `GET /api/operations/<id>` and call `POST /api/operations/<id>/validate`. Currently the panel is likely a stub.

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
`GET /api/graph` supports `source`, `target`, `story`, `limit`, `node_ids` filters (ADR-0011). The filter bar in the workbench should drive these query params and re-render the canvas on change.

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
- [ ] ADR-0015 written

**Blocked by:** ISSUE-5 (polling must work first)

---

## P3 — Future / deferred

---

### ISSUE-10 · [feature] Multi-goat relationship query

**Labels:** enhancement, future

**What and why:**  
All queries are scoped to the active goat. Some use cases (e.g. Xetrapal cross-graph reasoning) need to join relationships across two goats without switching the active goat.

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
- [ ] `docs/decisions/README.md` lists ADR-0001 through ADR-0013 (and future ones as added)
- [ ] Each row: number | title | status | one-line summary

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
