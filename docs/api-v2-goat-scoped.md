# MojoGOAT API v2 — Goat-Scoped Routes (spec)

**Status:** specified by [ADR-016](decisions/ADR-016-goat-scoped-api-remove-active-goat.md);
implemented on branch `feat/goat-scoped-routes` (target release v0.4.0, **unreleased and
uncommitted** as of 2026-11-01). This is the normative route spec with every status code;
`API_README.md` is the shorter practical reference.

There is **no active goat**. Every goat-level call names its goat in the path. In this document
`<goat>` is a goat's registry `name`.

## Errors common to all `/api/goats/<goat>/…` routes

| Status | When | Body |
|---|---|---|
| 404 | `<goat>` is not in the registry | `{"error": "Goat '<goat>' not found"}` |
| 404 | `<goat>` does not match the goat-name pattern (see below) | `{"error": "Goat '<goat>' not found"}` |
| 400 / 500 | goat is registered but cannot be opened | `{"error": "<underlying reason>"}` |
| 410 | a removed v1 route was called | `{"error": "Removed in API v2 (ADR-016): use <replacement>", "api_version": 2}` |

Other status codes per route (400 validation, 404 missing node or relationship, 409 conflict) are
unchanged from v1.

## Server and registry routes (unscoped)

| Route | Notes |
|---|---|
| `GET /health` | `{"status": "ok", "goat_count": N}` (no `active_goat`) |
| `GET /api/status` | adds `"api_version": 2`; drops `active_goat`, `goats[].is_active`, `goats[].is_default`; keeps `config`, `backends`, `goats`, `operations`, `timestamp` |
| `GET /api/registry`, `POST /api/registry` | unchanged; `POST` clears the goat cache |
| `GET /api/goats` | list of registry entries (no `is_active` / `is_default`) |
| `POST /api/goats` | create a goat. `name` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (else `400`). `make_active` / `make_default` → `400`. Text goats: `goat_path` optional — if given it must be absolute; if omitted the path is `$MOJOGOAT_DATA/<name>` and must resolve inside `$MOJOGOAT_DATA` (else `400`); `409` if the name or a text `goat_path` is already used |
| `GET /api/goats/<name>` | **new** — the goat's registry entry: `name`, `type`, `goatpath` (text), `goatname`, `description`, `created` |
| `GET /api/goats/<name>/summary` | unchanged |
| `DELETE /api/goats/<name>` | unchanged (`?purge=true` removes data); also drops the cached instance |

## Goat-scoped routes

All of these were previously unscoped (or under `/api/active-goat/`) and acted on the active goat.

### Nodes
- `GET /api/goats/<goat>/nodes`
- `POST /api/goats/<goat>/nodes` — body `{nodeid, labels?, …props}`; `409` if it exists
- `GET /api/goats/<goat>/nodes/<nodeid>`
- `PUT /api/goats/<goat>/nodes/<nodeid>`
- `DELETE /api/goats/<goat>/nodes/<nodeid>`
- `GET /api/goats/<goat>/nodes/label/<label>`

### Relationships
- `GET /api/goats/<goat>/relationships` — query params `source`, `target`, `story`, `limit`, and
  any other param as a props filter (e.g. `smriti_state`)
- `POST /api/goats/<goat>/relationships` — body `{source, target, story, …props}`; returns
  `relationship_id`
- `GET /api/goats/<goat>/relationships/<relationship_id>`
- `PATCH /api/goats/<goat>/relationships/<relationship_id>` — body `{…props}`
- `DELETE /api/goats/<goat>/relationships/<relationship_id>` — admin/test use only (ADR-008)

### Graph and analysis
- `GET /api/goats/<goat>/graph` — `{nodes, edges, node_count, edge_count}`; filters `source`,
  `target`, `story`, `limit`, `node_ids`, plus props filters (ADR-011)
- `GET /api/goats/<goat>/composition` — node count by label
- `GET /api/goats/<goat>/taxonomy` — relationship count by story

### Bulk and maintenance
- `POST /api/goats/<goat>/dump-relationships` — body `{filename}`
- `POST /api/goats/<goat>/import-relationships` — body `{filename}`; returns
  `{imported, skipped, errors}`
- `POST /api/goats/<goat>/compact` — text goats only; `400` for other types (ADR-007)

### Operations (ADR-012, ADR-014)
- `GET /api/goats/<goat>/operations` — **new in v2** (v1 had no list route) — only this goat's
  operations, oldest first
- `POST /api/goats/<goat>/operations` — body `{name, node_ids, params}`
- `GET /api/goats/<goat>/operations/<op_id>`
- `POST /api/goats/<goat>/operations/<op_id>/results`
- `POST /api/goats/<goat>/operations/<op_id>/validate` — body `{result_id, action}`; accepted
  results are written to `<goat>`
- `DELETE /api/goats/<goat>/operations/<op_id>`

An operation is reachable only under the goat that created it (`404` otherwise). Each operation
record carries a `goat` field; persisted operation files without one are skipped at startup with a
warning and left on disk.

## Removed (return `410 Gone`)

| Removed | Use instead |
|---|---|
| `GET /api/active-goat`, `POST /api/active-goat` | `GET /api/goats/<name>`; there is nothing to set |
| `GET /api/backend`, `POST /api/backend` | `POST /api/goats` with `type: text\|memory\|…` |
| `GET /api/direct/nodes` | `GET /api/goats/<goat>/nodes` |
| `GET /api/debug` | none (it diagnosed the module-identity split) |
| unscoped `/api/nodes…`, `/api/relationships…`, `/api/graph`, `/api/operations…`, `/api/active-goat/*` | the matching `/api/goats/<goat>/…` route |

## Client checklist
1. `GET /api/status`; require `api_version >= 2`, otherwise stop with a clear error.
2. `GET /api/goats/<name>`; on `404`, `POST /api/goats` to create it.
3. If you supplied a `goat_path` and the goat already existed, compare it with the entry's
   `goatpath` and fail on a mismatch.
4. Use only `/api/goats/<name>/…` routes from then on.
