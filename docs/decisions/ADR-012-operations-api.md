# ADR-012: Graph Operations API

**Date:** 2026-03-15
**Status:** Accepted

## Context

The MojoGOAT workbench (ADR-013) needs to support user-initiated graph operations such
as label propagation, where:

1. The user selects a set of nodes in the UI.
2. An external process (e.g. Xetrapal) is dispatched with the selection and any parameters.
3. The external process produces inferred results (new labels, new relationships via props).
4. A human reviews and validates each result before it is committed.

MojoGOAT must provide an API for submitting, tracking, and validating operations without
knowing what any specific operation does. Operations are opaque to MojoGOAT — it stores
their state and relays results; it does not execute them.

## Decision

### Data model

An **operation** has:
- `operation_id` — UUID assigned at creation
- `name` — caller-supplied string (e.g. `"label_propagation"`)
- `status` — `pending | running | awaiting_validation | completed | failed`
- `node_ids` — list of node IDs included in the selection
- `params` — arbitrary dict of operation parameters
- `results` — list of proposed changes (each has `type`, `payload`, `status: proposed|accepted|rejected`)
- `created`, `updated` — ISO-8601 timestamps

Operations are stored in memory (MemoryGoat-style dict) on the API process. They are
ephemeral — not written to the quad store. Only validated results that the human accepts
are written to the quad store via normal `create_relationship` / `add_node` calls.

### Endpoints

```
POST   /api/operations                     Create an operation (name, node_ids, params)
GET    /api/operations/<id>                Poll for status and results
POST   /api/operations/<id>/results        External process posts proposed changes
POST   /api/operations/<id>/validate       Human accepts/rejects individual results
DELETE /api/operations/<id>                Cancel / discard
```

### External process contract

An external process that wishes to handle an operation type:
1. Polls or is notified (via webhook URL in `params`) of a new operation.
2. Reads the node selection from `GET /api/operations/<id>`.
3. Fetches relevant graph data from `GET /api/graph?node_ids=...`.
4. Posts proposed changes to `POST /api/operations/<id>/results`.

MojoGOAT does not call out to external processes. The external process is responsible
for discovering and claiming operations.

### Result types

Each result entry in the `results` array has a `type` field:

| Type | Payload |
|------|---------|
| `add_node` | `{nodeid, ...props}` |
| `add_relationship` | `{source, target, story, ...props}` |
| `update_node` | `{nodeid, ...props}` |
| `update_relationship` | `{relationship_id, ...props}` |

When a result is accepted (`POST /api/operations/<id>/validate` with `action: "accept"`),
MojoGOAT executes the corresponding write against the active goat.

## Consequences

- Operations are in-memory only — a server restart loses pending operations. This is
  acceptable for the workbench use case (operations are interactive and short-lived).
- A future version could persist operations to the quad store as a special story type
  if durability is needed.
- MojoGOAT remains domain-agnostic. It does not know about label propagation, Xetrapal,
  smriti states, or any specific operation semantics.
- The external process integration is pull-based (polling). Webhook push can be added
  later by including a `callback_url` in the operation params — MojoGOAT would POST
  to that URL when status changes.
