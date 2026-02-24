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

**Action:** `git tag v0.2.0` then update xetrapal3's pyproject.toml to reference the tag.

---

## Item 2 — FalkorDBSmritiGraph in xetrapal3

**Context:** Lives in `/xpal-src/xetrapal3` — the SmritiGraph adapter over FalkorGoat.
**Prerequisite:** Item 1 (v0.2.0 tag) must be done first.
**Cross-reference:** See Phase 1 plan in `/xpal-src/xetrapal3/tasks/todo.md`.
