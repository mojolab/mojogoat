# ADR-0013: Graph Workbench UI

**Date:** 2026-03-15
**Status:** Accepted

## Context

MojoGOAT needs a first-class interactive graph workbench for exploring quads, running
graph operations, and validating inferred results. A basic embedded Flask template is
insufficient for this level of UX (multi-select, operation panels, validation queues,
layout switching).

## Decision

### Repository

The workbench lives in a **separate repository** (`mojogoat-ui` or similar). It is:
- A React single-page application
- Deployed independently (e.g. `npm run dev` on a separate port, or built and served as
  static assets from any web server)
- A pure API consumer — it contains no backend logic, makes no direct database calls,
  and speaks only to MojoGOAT's REST API

The MojoGOAT API (this repo) is the single source of truth. The UI has no privileged
access beyond what the API exposes.

### Technology

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Framework | React (Vite) | Modular, fast build, broad ecosystem |
| Graph rendering | Cytoscape.js | Best selection/event APIs, widest layout algorithm support (dagre, cose-bilkent, cola, grid, circle), strong compound-node support |
| Layout algorithms | cytoscape-dagre, cytoscape-cola, cytoscape-cose-bilkent | Hierarchical, force-directed constrained, and organic layouts respectively |
| State management | Zustand | Lightweight, no boilerplate, good for selection state |
| API layer | React Query (TanStack Query) | Polling for operation status, cache invalidation on write |
| Styling | Tailwind CSS | Utility-first, no design system dependency |

Cytoscape.js is chosen over Sigma.js/graphology because:
- Its selection model (`cy.elements(':selected')`) maps directly to the operation
  dispatch pattern in ADR-0012
- It has the richest set of maintained layout algorithm plugins
- It handles compound nodes, which may be useful for grouping by label or story type

### Core workbench panels

1. **Canvas** — Cytoscape.js graph with multi-select (box and click), zoom/pan
2. **Inspector panel** — shows quad fields and props for selected node or edge
3. **Filter bar** — live filter by story, node ID prefix, or prop value; calls `GET /api/graph`
4. **Layout switcher** — toggle between force (cose-bilkent), hierarchical (dagre), grid, circle
5. **Operations panel** — list operations, dispatch new ones against current selection,
   show status (pending/running/awaiting_validation)
6. **Validation queue** — review proposed changes from completed operations,
   accept or reject each result individually

### MojoGOAT API surface required

The workbench consumes:
- `GET /api/graph` (ADR-0011) — primary data load and filter
- `GET /api/active-goat/taxonomy` — for story colour coding
- `POST /api/operations` + `GET/POST /api/operations/<id>/*` (ADR-0012) — operations
- `PATCH /api/relationships/<id>` — direct prop edits from the inspector
- `POST /api/nodes`, `POST /api/relationships` — create from workbench

No new API endpoints are required beyond ADR-0011 and ADR-0012.

## Consequences

- The workbench is not bundled with MojoGOAT. Users run it separately.
- CORS is already enabled on the MojoGOAT API (flask-cors), so local dev (different port)
  works without changes.
- MojoGOAT has no React/Node.js build dependencies — the repos stay cleanly separated.
- Future visualisation approaches (WebGL for large graphs, timeline view, matrix view)
  can be added to the workbench without touching the API.
