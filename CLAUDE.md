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
│   │   ├── falkorgoat.py      ← FalkorDB backend (done)
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
- `relationship_id` is an opaque string generated at write time — treat as opaque, never parse it
  - TextGoat generates `{goatname}:{10char_base62}` (e.g. `xetrapal:Kj8mNpQr4t`) — see ADR-0006
  - FalkorGoat/Neo4jGoat/MemoryGoat generate UUID v4 strings — see ADR-0002
- `timestamp` is always an ISO-8601 string — never a Python `datetime` object
- `story` is whatever the caller passes — MojoGOAT is domain-agnostic, never validate it
- `**props` are stored and returned as-is — MojoGOAT does not interpret them
- Application flow must never call `delete_relationship` — use `**props` for invalidation
  (e.g. `smriti_state="invalidated"`). `delete_relationship` exists for admin/test use only — see ADR-0008

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
Every commit carries `Coding-Agent:` (`claude`, `opencode`, or `manual`) and
`Model:` trailers via the `prepare-commit-msg` hook (see `.githooks/`; `Model:`
needs `claudia` on `PATH`). Enable it with: `git config core.hooksPath .githooks`.

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
- [x] Neo4jGoat async pytest suite — `test/test_newneo4jgoatcopilot.py` (skipped gracefully when `neo4j` not installed)
- [ ] MongogoatModels — deferred
- [x] FalkorDB backend — `falkorgoat.py`, 25 unit + 3 integration tests

---

## Next Steps

Tag `v0.2.0` (all Phase 1 items complete), then update Xetrapal's `pyproject.toml` to use the tag:
```toml
mojogoat = { git = "https://github.com/you/mojogoat", tag = "v0.2.0" }
```
MongogoatModels remains deferred.
