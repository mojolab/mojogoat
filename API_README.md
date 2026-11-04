# MojoGOAT API

A RESTful API for the Graph of All Things (GOAT) system, supporting different storage backends and CRUD operations.

> **API v2 (v0.4.0, [ADR-016](docs/decisions/ADR-016-goat-scoped-api-remove-active-goat.md)) — breaking.**
> There is no "active goat". Every goat-level route names its goat: `/api/goats/<goat>/…`. The v1
> routes (`/api/active-goat*`, `/api/backend`, and the unscoped `/api/nodes`, `/api/relationships`,
> `/api/graph`, `/api/operations`) return `410 Gone` with the replacement named. Clients must check
> `api_version >= 2` in `GET /api/status`. The normative route spec, with every status code, is
> [docs/api-v2-goat-scoped.md](docs/api-v2-goat-scoped.md).

## Running the API

```bash
./run_mojogoat_api.sh [options]
```

Options:
- `--registry, -r PATH`: Path to the registry file (default: $MOJOGOAT_REGISTRY or /xpal-data/conf/goat_registry.json)
- `--port, -p PORT`: Port to listen on (default: 5000)
- `--host HOST`: Host to bind to (default: 0.0.0.0)
- `--debug, -d`: Enable debug mode
- `--help, -h`: Show this help message

Environment: `MOJOGOAT_REGISTRY` (registry file), `MOJOGOAT_DATA` (default directory for text goats
created without an explicit `goat_path`, default `/xpal-data/goats`), `MOJOGOAT_OPERATIONS_DIR`
(persisted operations, default `/xpal-data/run/operations`).

Example:
```bash
./run_mojogoat_api.sh -r /path/to/registry.json -p 8080 -d
```

## Concepts

- **Goat:** one named graph store registered in the registry file. Its `type` is `text`, `memory`,
  `neo4j` or `falkordb`. A text goat's data directory (`goatpath`) is chosen per goat and can be
  anywhere; the registry file itself can live elsewhere.
- **Goat names** are URL path segments and must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.
- **No server-wide state selects a goat.** Each request carries its goat in the path, so several
  clients can use different goats on one server at the same time.
- **Limitation:** a goat should have a single writer that issues writes one at a time. Concurrent
  relationship writes to one text goat fail or hang (pre-existing; see ISSUE-21).

## API Endpoints

### Server

| Route | Purpose |
|---|---|
| `GET /health` | Liveness: `{"status": "ok", "goat_count": N}` |
| `GET /api/status` | Self-test: `api_version` (2), `config`, `goats`, `backends`, endpoint index |
| `GET /api/registry` | Current registry file path |
| `POST /api/registry` | Body `{"path": "/path/to/registry.json"}`; loads it, or creates an empty one if absent |

### Goat management

#### List goats
```
GET /api/goats
```

#### Get one goat
```
GET /api/goats/{goat}
```
Returns the goat's registry entry (`name`, `type`, and `goatpath` for text goats). Use it to confirm
where a goat's data lives.

#### Create a goat
```
POST /api/goats
```
Body:
```json
{
  "name": "my_goat",
  "type": "text",
  "description": "My goat description",
  "goat_path": "/path/to/goat"
}
```
- `type`: `text`, `memory`, `neo4j` or `falkordb`.
- Text goats: `goat_path` is optional but must be absolute if given; if omitted the path is
  `$MOJOGOAT_DATA/<name>`. An unwritable path is rejected with `400` at create time.
- Neo4j: `config_path` (path to a JSON config) is required. FalkorDB: optional `host`, `port`,
  `graph_name`, `password`.
- `make_active` / `make_default` are removed and return `400`.
- `409` if the name, or a text `goat_path`, is already registered. `400` for an invalid name.

#### Goat summary
```
GET /api/goats/{goat}/summary
```
Node count, relationship count and taxonomy.

#### Remove a goat
```
DELETE /api/goats/{goat}?purge=true
```
Without `purge` only the registry entry is removed. With `purge=true` the storage is destroyed too
(irreversible).

### Node operations

All under `/api/goats/{goat}`:

| Route | Purpose |
|---|---|
| `GET /nodes` | All nodes |
| `GET /nodes/{nodeid}` | One node |
| `GET /nodes/label/{label}` | Nodes by label |
| `POST /nodes` | Create or update; body `{"nodeid": "id", "labels": [...], ...props}`; `nodeid` must not contain `/` |
| `PUT /nodes/{nodeid}` | Update properties |
| `DELETE /nodes/{nodeid}` | Delete |

### Relationship operations

All under `/api/goats/{goat}`:

| Route | Purpose |
|---|---|
| `GET /relationships` | List. Query params: `source`, `target`, `story`, `limit`, `offset`; any other param filters on a property (e.g. `smriti_state=pending`) |
| `GET /relationships/{relationship_id}` | One relationship |
| `POST /relationships` | Create; body `{"source": "a", "target": "b", "story": "knows", ...props}`; returns `relationship_id` |
| `PATCH /relationships/{relationship_id}` | Update properties (this is how callers invalidate; see ADR-008) |
| `DELETE /relationships/{relationship_id}` | Admin/test use only (ADR-008) |

### Goat-level operations

All under `/api/goats/{goat}`:

| Route | Purpose |
|---|---|
| `GET /graph` | `{nodes, edges, node_count, edge_count}`; filters `source`, `target`, `story`, `limit`, `node_ids`, plus property filters (ADR-011) |
| `GET /composition` | Node count by label |
| `GET /taxonomy` | Relationship count by story |
| `POST /dump-relationships` | Body `{"filename": "/path/to/output.txt"}` |
| `POST /import-relationships` | Body `{"filename": "..."}`; returns `{imported, skipped, errors}` |
| `POST /compact` | Compact TextGoat snapshots (text goats only, ADR-007) |

### Operations API (ADR-012, scoped per goat)

Under `/api/goats/{goat}/operations`: `GET` (list, new in v2), `POST`, `GET /{id}`,
`POST /{id}/results`, `POST /{id}/validate`, `DELETE /{id}`. An operation is reachable only under
the goat that created it; accepting a result writes to that goat.

### Errors common to goat-scoped routes

| Status | Meaning |
|---|---|
| `404` | The goat is not in the registry (or its name is invalid) |
| `400` / `500` | The goat is registered but cannot be opened |
| `410` | A removed v1 route; the body names the replacement |

## Testing

Offline unit tests (no services needed):
```bash
uv run --extra dev pytest tests/ -m "not integration"
```
See [API_TEST_README.md](API_TEST_README.md) for the live-server CLI tests and the Postman collection.
