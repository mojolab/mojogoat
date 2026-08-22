# ADR-0010: Backend Hierarchy — Neo4j Primary, FalkorDB Opt-In

**Date:** 2026-03-15
**Status:** Accepted

## Context

FalkorDB was introduced in Phase 1 as the recommended "serious" graph backend and was
included in the `auto` backend selection order. In practice:

- FalkorDB is Redis-based and requires a running Redis-compatible server with the FalkorDB
  module loaded — a non-trivial operational dependency.
- In development environments it is frequently unavailable, causing `auto` mode to silently
  fall through to TextGoat without any signal that the intended backend was not used.
- Neo4j is already fully implemented (`neo4jgoat.py`), has a richer Cypher feature set,
  broader community adoption, and is the more natural "serious" graph backend for a quad
  store that uses property-graph semantics.

## Decision

1. **Neo4j is the primary production graph backend.** It is the recommended backend for
   any deployment that needs persistence beyond flat files.

2. **FalkorDB is retained but demoted to opt-in.** It is suitable for Redis-native
   deployments where FalkorDB is already running. It is not removed from the codebase.

3. **`auto` mode no longer probes FalkorDB or Neo4j.** Auto-selection order becomes:
   `text → memory`. Both Neo4j and FalkorDB require an explicitly configured external
   service and must be selected intentionally.

4. **Registry type strings are unchanged.** `"type": "neo4j"` and `"type": "falkordb"`
   continue to work exactly as before in `POST /api/goats` and `POST /api/backend`.

5. **Documentation and `GET /api/status` backend descriptions** are updated to reflect
   Neo4j as the recommended production backend.

## Consequences

- `POST /api/backend` with `type: "auto"` will never select Neo4j or FalkorDB, even if
  both are reachable. Callers that want Neo4j must pass `type: "neo4j"` explicitly.
- The `_probe_falkordb` helper in `mojogoatapi.py` is retained but removed from the
  `auto` code path.
- Integration tests for both Neo4j and FalkorDB remain in the test suite, marked
  `integration`, and are skipped when the service is not available.
