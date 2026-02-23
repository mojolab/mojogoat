# CLAUDE.md — MojoGOAT Development Guidelines

This file tells Claude Code how to work on this project. Read it at the start of every session.
Also read `tasks/lessons.md` if it exists.

---

## What This Project Is

MojoGOAT (Graph of All Things) is a quad storage engine. It stores typed relationships in the
form `source | story | target | timestamp` across multiple backends (TextGoat, Neo4jGoat,
FalkorGoat, MongogoatModels). It is domain-agnostic — it does not know about Smriti validation
states, Xetrapal URIs, or any caller's epistemology. Callers store what they need via `**props`.

MojoGOAT is used as a dependency by Xetrapal (`/xpal-src/xetrapal3`), which wraps it in a
SmritiGraph adapter layer. Do not bleed Xetrapal's domain logic into MojoGOAT.

---

## Repository Layout

```
mojogoat/
├── CLAUDE.md                  ← you are here
├── tasks/
│   ├── todo.md                ← current session plan
│   └── lessons.md             ← consolidated lessons, pruned regularly
├── mojogoat/
│   ├── goatbases/
│   │   ├── textgoat.py        ← file-based backend (done)
│   │   ├── newneo4jgoatcopilot.py  ← Neo4j async backend (done)
│   │   ├── falkorgoat.py      ← FalkorDB backend (Phase 1 task)
│   │   ├── neo4jgoat.py       ← retired stub (raises ImportError)
│   │   └── mongogoat/         ← MongoDB+Postgres backend (deferred)
│   └── __init__.py
├── test/
├── pyproject.toml
└── mojogoatapi.py             ← Flask REST API (not used by Xetrapal directly)
```

---

## How to Work on This Project

### Triage first

Before doing anything, classify the task:

| Type | Threshold | Process |
|------|-----------|---------|
| Trivial | Single file, obvious fix | Just do it. No todo.md. No check-in. |
| Routine | 2-5 files, clear scope | Write todo.md items, execute, summarise. |
| Non-trivial | Cross-backend, interface change, ambiguous | Plan first. Check in before implementing. |

When in doubt, treat as non-trivial.

### When something goes wrong

Stop. Do not keep pushing. Re-plan from the last known good state.
If the correct behaviour is ambiguous — particularly around the quad schema, backend
interface contract, or async semantics — **stop and ask**. Do not invent intended behaviour.
A confident wrong fix is worse than a question.

---

## Coding Standards

- Python 3.11+, async-first (`asyncio`), typed (`mypy`-clean)
- `uv` for dependency management — never bare `pip install` in project code
- No hardcoded credentials, hostnames, or ports in source — always accept via constructor
- Every backend implements the same interface — new backends are drop-in replacements
- Simplicity wins over elegance **unless the simple version creates maintenance debt**
- Touch only what the task requires. Minimal diff.
- 4-space indentation, 100 character line limit
- snake_case for functions/variables, CamelCase for classes
- Docstrings on classes and public methods; inline comments for non-obvious logic

---

## Quad Model — Handle With Care

The quad model is the contract between MojoGOAT and all callers. Do not change it
without understanding the downstream impact on Xetrapal's SmritiGraph layer.

```
source | story | target | timestamp | relationship_id | **props
```

Rules:
- `relationship_id` is always a UUID v4 string generated at write time — never an integer
- `timestamp` is always an ISO-8601 string — never a Python `datetime` object
- `story` is whatever the caller passes — MojoGOAT is domain-agnostic, never validate it
- `**props` are stored and returned as-is — MojoGOAT does not interpret them
- Never delete relationships — callers manage their own invalidation via `**props`

### Cypher relationship model (for FalkorGoat and Neo4jGoat)

Two relationship types only:
- `is_the_same_as` — for identity/equivalence relationships
- `is_connected_to` — for all others; `story` stored in a `stories` property array

```cypher
(a)-[:is_connected_to {
    relationship_id: "uuid",
    stories: ["navigated to"],
    timestamp: "2026-02-23T14:22Z",
    state: "pending"
}]->(b)
```

Query by story: `MATCH (a)-[r:is_connected_to]->(b) WHERE 'navigated to' IN r.stories`

---

## Verification Before Done

- Run tests before marking anything complete: `uv run pytest test/`
- Integration tests require live services — skip by default: `uv run pytest test/ -m "not integration"`
- For any backend change: verify the round-trip — `create_relationship()` → `get_relationships()` → correct data returned
- For async changes: confirm `await` is used correctly — no sync calls blocking the event loop
- For new backends: run the same test scenarios as `test_textgoat_async.py`

---

## Self-Improvement

After any correction, add a concise rule to `tasks/lessons.md`.
Format: `[date] — [what went wrong] — [rule that prevents it]`

Prune `tasks/lessons.md` when it exceeds 20 entries. Keep it short enough to read in under 2 minutes.

---

## Git Workflow

Branch naming: `phase/N-description` for phase work, `fix/short-description` for fixes.
Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

---

## What Not To Touch

- `mojogoatapi.py` — Flask REST API, not used by Xetrapal. Do not break its interface.
- `mojogoat/goatbases/mongogoat/` — deferred. Do not touch until TextGoat and Neo4jGoat are stable.
- `neo4jgoat.py` — already retired as a stub. Do not resurrect py2neo.
- `/xpal-src/xetrapal3/` — sibling Xetrapal repo. Do not modify without explicit instruction.
- Any file outside `/xpal-src/mojogoat/` unless explicitly instructed.

---

## Modernisation Roadmap (for Xetrapal Phase 1 integration)

### Status (as of 2026-02-23)
- [x] `pyproject.toml` created and valid
- [x] TextGoat — async, UUID v4, ISO-8601, `**props`, full async pytest suite
- [x] Neo4jGoat (`newneo4jgoatcopilot.py`) — async, UUID v4, ISO-8601, `**props`
- [x] `neo4jgoat.py` (py2neo) — retired, raises `ImportError`
- [ ] Neo4jGoat async pytest suite — manual test script exists; needs proper `pytest` variant
- [ ] MongogoatModels — deferred
- [ ] FalkorDB backend — see Phase 1 section below

---

## Phase 1: FalkorDB Backend

Xetrapal Phase 1 uses FalkorDB as the development graph backend. MojoGOAT needs a
`FalkorGoat` backend before `FalkorDBSmritiGraph` can be built in Xetrapal.

FalkorDB speaks Cypher and has a Python client (`falkordb` package). The backend will be
thin — structurally identical to `newneo4jgoatcopilot.py` with FalkorDB client calls.

### Tasks (work in order)

1. **Add `falkordb` to `pyproject.toml`**
   ```toml
   [project.optional-dependencies]
   falkordb = ["falkordb>=1.0"]
   ```
   Run `uv sync --extra falkordb` to verify.

2. **Create `mojogoat/goatbases/falkorgoat.py`**
   - Class `FalkorGoat` with the same interface as `Neo4jGoat`
   - Constructor: `__init__(self, host, port, graph_name)` — connects via `falkordb.FalkorDB()`
   - All methods `async def` from the start (use `asyncio.to_thread` to wrap FalkorDB's
     synchronous client calls until an async client is available)
   - `create_relationship(source, target, story, **props)` — stores `story` in a `stories`
     property array on the edge (Cypher model: `is_connected_to` or `is_the_same_as`)
   - Two relationship types only: `is_the_same_as` and `is_connected_to`
   - All other properties (`state`, `timestamp`, `relationship_id`, `**props`) stored on the edge
   - `get_relationships(source, target, story)` — queries by `story IN r.stories`

3. **Export from `__init__.py`**
   ```python
   from .falkorgoat import FalkorGoat
   ```

4. **Write async pytest suite `test/test_falkorgoat_async.py`**
   - Mirror the structure of `test/test_textgoat_async.py`
   - Mark integration tests `@pytest.mark.integration` (require live FalkorDB)
   - Unit tests mock the FalkorDB client
   - Test: UUID v4 IDs, ISO-8601 timestamps, `**props` round-trip, `state` field stored/retrieved,
     `is_the_same_as` vs `is_connected_to` relationship type routing

5. **Tag `v0.2.0`** once FalkorGoat tests pass and Neo4jGoat pytest suite is added.
   Then update Xetrapal to the tag reference:
   ```toml
   mojogoat = { git = "https://github.com/you/mojogoat", tag = "v0.2.0" }
   ```

### Testing
Run existing tests after each change: `uv run pytest test/`
Integration tests (requiring live services) are marked `@pytest.mark.integration` and
skipped by default: `uv run pytest test/ -m "not integration"`

### Xetrapal dependency setup
Xetrapal references MojoGOAT via:
```toml
# xetrapal3/pyproject.toml
[tool.uv.sources]
mojogoat = { path = "../mojogoat", editable = true }
```
Once stable, tag a release (`git tag v0.2.0`) and switch Xetrapal to a git tag reference.
