# ADR-011: Graph Data API

**Date:** 2026-03-15
**Status:** Accepted

## Context

All existing REST endpoints operate on quads (source, story, target, timestamp) or nodes
individually. There is no endpoint that returns the full graph structure in a format
suitable for visualisation or graph algorithm consumption.

The MojoGOAT workbench (ADR-013) and any external graph tool need a single endpoint
that returns the active goat's data as a property graph (nodes + edges) with optional
filters. This endpoint is backend-agnostic — it assembles the response from the existing
`get_nodes()` and `get_relationships()` interface methods.

## Decision

Add `GET /api/graph` to the routes layer with the following contract:

### Response format

```json
{
  "nodes": [
    { "id": "type:jeeva", "labels": ["jeeva"], "...props": "..." }
  ],
  "edges": [
    {
      "id": "uuid",
      "source": "type:jeeva",
      "target": "val:foo",
      "story": "is a",
      "timestamp": "2026-03-15T10:00:00",
      "...props": "..."
    }
  ],
  "node_count": 12,
  "edge_count": 34
}
```

### Query parameters (all optional)

| Parameter | Description |
|-----------|-------------|
| `source`  | Filter edges by source node ID |
| `target`  | Filter edges by target node ID |
| `story`   | Filter edges by story |
| `limit`   | Max edges returned |
| `node_ids`| Comma-separated list — return only these nodes and edges between them |
| Any other param | Forwarded as a `props` filter on edges |

### Node inclusion rule

Nodes are returned if:
- They appear as `source` or `target` in at least one returned edge, **or**
- They are explicitly requested via `node_ids`.

Orphan nodes (no edges after filtering) are not returned unless `node_ids` is used.
This prevents unbounded payloads when a goat has many isolated nodes.

## Consequences

- The endpoint assembles from two calls (`get_nodes`, `get_relationships`) and does
  client-side join for node properties. This is acceptable at current scales.
- No new backend interface methods are required.
- A future `GET /api/graph/export/gexf` can be added alongside this endpoint without
  changing the data model.
- The workbench (ADR-013) uses this endpoint as its primary data source.
