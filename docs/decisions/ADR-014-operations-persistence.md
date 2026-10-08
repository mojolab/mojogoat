# ADR-014: Persist Operations to Disk

**Date:** 2026-07-26
**Status:** Accepted

## Context

ADR-012 introduced the Operations API and accepted in-memory-only storage as fine for the
interactive workbench use case, noting: *"A future version could persist operations to the quad
store as a special story type if durability is needed."*

In practice, external processes that propose operations (any caller following the ADR-012
"external process" contract) may leave an operation `awaiting_validation` for a while before a
human reviews it — a server restart in that window silently loses the proposed changes with no
way to recover them.

## Decision

`mojogoat/operations.py` now also persists each operation to disk on every mutation
(`create_operation`, `post_results`, `validate_result`, `delete_operation`), and reloads them at
process startup:

- `MOJOGOAT_OPERATIONS_DIR` (default `/xpal-data/run/operations/`) holds one JSON file per
  operation, named `<operation_id>.json`.
- Writes are best-effort — a persistence failure does not fail the API call; the in-memory dict
  remains the source of truth at runtime. This is a write-through cache, not a redesign.
- `mojogoatapi.py`'s `__main__` startup path (i.e. only when actually running the server, not when
  the module is imported for tests) calls `operations.load_persisted()` to reload any operations
  left on disk from a previous run. It skips operation IDs already present in memory, so it never
  clobbers state that's already been recreated since startup.

This does not change the Operations API's contract, response shapes, or the "operations are opaque
to MojoGOAT" principle from ADR-012 — it only makes the existing in-memory state durable.

## Consequences

- Small amount of additional disk I/O per operation mutation, scoped to `/xpal-data` (this
  deployment's local/session data directory, not committed to the repo).
- Tests that exercise the Operations API must isolate `MOJOGOAT_OPERATIONS_DIR` to a temp
  directory (see `tests/test_api.py`'s `setUp`/`tearDown`) so they don't write into the real
  `/xpal-data/run/operations/` — mirroring how the same tests already isolate the registry file.
- `tests/test_operations_persistence.py` covers create/post/validate/delete persisting correctly,
  and reloading after a simulated restart.
