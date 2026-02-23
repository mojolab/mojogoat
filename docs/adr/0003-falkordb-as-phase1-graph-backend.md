# ADR-0003: FalkorDB as the Phase 1 graph backend for Xetrapal

Date: 2026-02-23
Status: Accepted

## Context

Xetrapal Phase 1 needs a live graph backend for its SmritiGraph layer.
MojoGOAT already has a Neo4jGoat backend, but running Neo4j in development
requires a JVM, significant memory, and either a Docker container or a
licensed installation. The Xetrapal development environment targets lightweight,
Redis-adjacent infrastructure.

FalkorDB is a graph database built as a Redis module. It speaks Cypher (the same
query language as Neo4j) and has an official Python client (`falkordb`) with an
async interface. It runs in the same Redis process already present in the stack.

## Options considered

| Option | Notes |
|---|---|
| Neo4j (existing Neo4jGoat) | Heavy; JVM dependency; overkill for Phase 1 dev |
| Pure in-memory graph | No persistence; not suitable for integration testing |
| NetworkX / Python graph | No Cypher; incompatible with the Cypher relationship model |
| FalkorDB | Cypher-compatible; lightweight; Redis-backed; async client available |

## Decision

FalkorDB is the Phase 1 development graph backend. `FalkorGoat`
(`mojogoat/goatbases/falkorgoat.py`) implements the full MojoGOAT backend
interface using `falkordb.asyncio`.

The `falkordb` package is an optional dependency (`pip install mojogoat[falkordb]`)
so that installations not using the graph backend do not pull in the Redis client.

Neo4jGoat remains available and unchanged for production deployments.

## Consequences

- Xetrapal Phase 1 can develop against FalkorDB without running a full Neo4j
  instance.
- Because both backends use the same two-type Cypher model (ADR-0004), switching
  from FalkorDB to Neo4j in production is a constructor swap, not a code change.
- FalkorDB's Python async client wraps synchronous operations internally; if a
  native async client becomes available it can be adopted transparently.
- Integration tests for FalkorGoat require a running Redis+FalkorDB instance and
  are marked `@pytest.mark.integration`.
