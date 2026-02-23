# ADR-0002: UUID v4 relationship IDs generated at write time

Date: 2026-02-23
Status: Accepted

## Context

The original TextGoat implementation identified relationships by positional index
(`rel_0`, `rel_1`, …). These IDs are derived from a line's position in the
snapshot file. When any relationship is deleted, every subsequent ID shifts,
making stored IDs stale. The old Neo4jGoat used py2neo's internal integer IDs,
which are database-specific and not portable across backends.

Callers (Xetrapal) need stable, portable IDs to reference individual relationships
— for example, to later update props such as `state` without re-querying.

## Options considered

| Option | Problem |
|---|---|
| Positional index (`rel_N`) | Breaks on deletion; not portable |
| Database-generated integer | Backend-specific; not portable |
| Content hash (uuid5) | Deterministic but collides on duplicate quads |
| UUID v4 at write time | Globally unique, backend-agnostic, stable |

## Decision

Every `create_relationship()` call generates a `str(uuid4())` and stores it:

- **TextGoat**: as the 5th pipe-delimited field in the `.gq` snapshot line
- **Neo4jGoat / FalkorGoat**: as a `relationship_id` property on the Cypher edge

The UUID is returned in the response dict and is the key used by
`delete_relationship()` and `update_relationship_props()`.

Old TextGoat files without a 5th field (4-field legacy format) get a stable
read-time ID derived via `uuid5(NAMESPACE_URL, line_content)`. These IDs are
not persisted; they become permanent only when the relationship is re-written.

## Consequences

- Relationship IDs are stable across deletions and backend migrations.
- IDs are the same shape and type regardless of which backend is active.
- The `relationship_id` field is now part of the quad model contract — all
  backends must generate and return it.
- Legacy `.gq` files can be read without migration, but deletion of legacy
  relationships requires the uuid5-derived ID (which is stable as long as the
  line content is unchanged).
