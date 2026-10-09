# MojoGOAT Architecture

> **Note:** `CLAUDE.md` is the authoritative reference for development guidelines.
> This document describes the runtime architecture for general readers.

---

## The Quad Model

MojoGOAT stores typed relationships as quads:

```
source | story | target | timestamp | relationship_id | **props
```

| Field | Type | Notes |
|---|---|---|
| `source` | string | Source node ID |
| `story` | string | Relationship type — domain-agnostic, never validated |
| `target` | string | Target node ID |
| `timestamp` | ISO-8601 string | Set at write time |
| `relationship_id` | UUID v4 string | Set at write time, never an integer |
| `**props` | key-value pairs | Stored and returned as-is |

Example:
```
alice|navigated to|dashboard|2026-02-23T14:22:01.123456|3f2e1a...|state=pending
```

---

## Storage Backends

All backends implement the same async interface and are drop-in replacements.

### TextGoat (`goatbases/textgoat.py`)

File-based storage — no external services required.

- Nodes stored as JSON files under `{goatpath}/nodes/{nodeid}`
- Relationships stored as pipe-delimited lines in snapshot files under `{goatpath}/snapshots/`
- `goatrels.gq` holds a pointer to the current snapshot file
- Extra props stored as a JSON blob in field 6 of each line

**Use for**: development, testing, local datastores, git-versioned data.

### Neo4jGoat (`goatbases/newneo4jgoatcopilot.py`)

Async Neo4j backend using the official `neo4j` driver.

- Two Cypher relationship types: `is_connected_to` and `is_the_same_as`
- `story` stored in a `stories` list property: `WHERE $story IN r.stories`
- `relationship_id` stored as a property on the edge

**Use for**: production graph workloads requiring traversal and graph algorithms.

### FalkorGoat (`goatbases/falkorgoat.py`)

Async FalkorDB backend (Redis-based graph, Cypher query language).

- Same two-type Cypher model as Neo4jGoat
- Uses `falkordb.asyncio` client
- FalkorDB is the development graph backend for Xetrapal Phase 1

**Use for**: Xetrapal Phase 1 integration, development environments with Redis.

### MongoDB + PostgreSQL (`goatbases/mongogoat/`) — deferred

Hybrid backend: MongoDB for node documents, PostgreSQL for relationship records.

- **Status**: implementation exists but async migration is deferred
- Do not modify until TextGoat and Neo4jGoat are stable

---

## Flask REST API (`mojogoatapi.py`)

A registry-backed HTTP API for managing multiple named goat instances.

- Not used by Xetrapal directly — Xetrapal imports goat classes as a Python library
- Registry stored at `$MOJOGOAT_REGISTRY` (default: `/xpal-data/conf/goat_registry.json`)
- Supports `text`, `neo4j`, and `mongopg` goat types

---

## Xetrapal Integration

Xetrapal (`/xpal-src/xetrapal3`) references MojoGOAT as an editable dependency:

```toml
# xetrapal3/pyproject.toml
[tool.uv.sources]
mojogoat = { path = "../mojogoat", editable = true }
```

Xetrapal's `SmritiGraph` layer wraps `FalkorGoat` and adds domain logic
(validation states, URI schemes, etc.). MojoGOAT itself remains domain-agnostic.
