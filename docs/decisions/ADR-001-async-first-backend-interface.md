# ADR-001: Async-first backend interface

Date: 2026-02-23
Status: Accepted

## Context

MojoGOAT is consumed as a library by Xetrapal, whose SmritiGraph layer is fully
async (`asyncio`). If MojoGOAT's backend methods were synchronous, every call from
Xetrapal would either block the event loop or require explicit thread-pool
wrapping at the call site — a burden on every caller, not just one.

The three backends in scope (TextGoat, Neo4jGoat, FalkorGoat) have different I/O
primitives: file I/O, Neo4j driver calls, and Redis/FalkorDB calls respectively.
All three have async-capable libraries available.

## Decision

All public CRUD methods on every backend class are declared `async def`.

- **TextGoat**: file I/O via `aiofiles`
- **Neo4jGoat**: `AsyncGraphDatabase` from the official `neo4j` driver
- **FalkorGoat**: `falkordb.asyncio.FalkorDB`

The Flask REST API layer (`mojogoatapi.py`) uses `asgiref` so that async route
handlers can `await` backend calls directly. The Flask layer is not used by
Xetrapal; this is a convenience for the HTTP interface only.

## Consequences

- Xetrapal can `await` any backend method without wrapping or thread pools.
- All backends share the same async interface — they are drop-in replaceable.
- Sync callers (scripts, notebooks) must use `asyncio.run()` or an event loop.
- The MongoDB+PostgreSQL backend (deferred) must also be async when it is
  eventually migrated.
