# ADR-016: Goat-Scoped API — Remove the "Active Goat"

**Date:** 2026-10-31
**Status:** Accepted — implementation pending (target release v0.4.0, **breaking**)

> **Numbering note:** an `0015-xpal-data-runtime-ownership.md` ADR exists on the unmerged branch
> `docs/adr-0015-and-samples`. This ADR is numbered 016 to avoid a clash when that branch merges.

## Context

MojoGOAT's REST API keeps one server-wide global, `active_goat`. Every data route
(`/api/nodes`, `/api/relationships`, `/api/graph`, `/api/operations`, `/api/active-goat/*`) acts on
whichever goat that global currently points at. Clients select a goat with
`POST /api/active-goat` and then issue unscoped calls.

This has caused concrete problems:

1. **Module-identity split.** `python mojogoatapi.py` runs as `__main__`; `routes.py` does
   `import mojogoatapi`, which loads a *second* copy of the module with its own `active_goat`.
   Switching goats updated one copy and `routes.py` read the other, so writes landed in the wrong
   goat (mojolab/mojogoat#20; fixed by `set_active_goat_ref`, a workaround, not a cure).
2. **Shared mutable state between clients.** The selection is per-server, not per-client. Two
   clients using different goats overwrite each other's selection between a `POST /api/active-goat`
   and the call that follows it. Xetrapal's management client already works around this with a
   switch-then-restore sequence (`xetrapal/manage/client.py: fetch_smritis`), which is not safe
   under concurrency.
3. **The target deployment needs it gone.** Two Xetrapal processes run in parallel, each with its
   own text goat (`xpal1goat` under `/xpal-data/goats/`, `AVGFGoat` under `/xpal-data-remote/`),
   against one MojoGOAT server. That cannot work with a global selection.

Registry entries already carry their own `goatpath`, so goats are already independently addressable
on disk; only the HTTP surface treats one of them as special.

## Decision

**There is no active goat.** Every goat-level operation names its goat in the URL. The server holds
no per-client or per-server "current goat" state.

### 1. Route shape

All data routes move under `/api/goats/<goat>/…`. The old unscoped routes are removed.

| Old (removed) | New |
|---|---|
| `GET/POST /api/nodes` | `GET/POST /api/goats/<goat>/nodes` |
| `GET/PUT/DELETE /api/nodes/<nodeid>` | `GET/PUT/DELETE /api/goats/<goat>/nodes/<nodeid>` |
| `GET /api/nodes/label/<label>` | `GET /api/goats/<goat>/nodes/label/<label>` |
| `GET/POST /api/relationships` | `GET/POST /api/goats/<goat>/relationships` |
| `GET/PATCH/DELETE /api/relationships/<id>` | `GET/PATCH/DELETE /api/goats/<goat>/relationships/<id>` |
| `GET /api/graph` | `GET /api/goats/<goat>/graph` |
| `GET /api/active-goat/composition` | `GET /api/goats/<goat>/composition` |
| `GET /api/active-goat/taxonomy` | `GET /api/goats/<goat>/taxonomy` |
| `POST /api/active-goat/dump-relationships` | `POST /api/goats/<goat>/dump-relationships` |
| `POST /api/active-goat/import-relationships` | `POST /api/goats/<goat>/import-relationships` |
| `POST /api/active-goat/compact` | `POST /api/goats/<goat>/compact` |
| `GET/POST /api/operations`, `/<id>`, `/<id>/results`, `/<id>/validate`, `DELETE /<id>` | same paths under `/api/goats/<goat>/operations…` |

**Kept unchanged:** `GET/POST /api/goats`, `GET /api/goats/<name>/summary`,
`DELETE /api/goats/<name>`, `GET/POST /api/registry`, `GET /api/status`, `GET /health`.

**Added:** `GET /api/goats/<name>` — returns that goat's registry entry (`name`, `type`,
`goatpath`, `created`, …). It replaces `GET /api/active-goat` for clients that need to verify where a
goat's data actually lives.

**Also added:** `GET /api/goats/<goat>/operations` (list this goat's operations). v1 had no list
route, so this is new rather than a move; `mojogoat-ui` already calls `GET /api/operations`, which
never existed in the server.

**Removed with no replacement:** `GET/POST /api/active-goat`, `GET/POST /api/backend` (selecting an
ad-hoc backend as "the" goat — create a `memory` or `text` goat with `POST /api/goats` instead),
`GET /api/direct/nodes`, `GET /api/debug` (existed only to diagnose the module-identity split).

Full request/response detail: [`docs/api-v2-goat-scoped.md`](../api-v2-goat-scoped.md).

### 2. Hard failure for stale clients

Removed routes are not silently 404. For the v0.4.0 release they return **`410 Gone`** with a JSON
body naming the replacement, e.g.
`{"error": "Removed in API v2 (ADR-016): use /api/goats/<goat>/nodes", "api_version": 2}`.
The stubs are dropped in a later release.

`GET /api/status` gains `"api_version": 2`. Clients must check it and refuse to proceed against a
server reporting a lower value or none. There is no compatibility mode.

### 3. Goat resolution

The server keeps a cache `{goat_name: GoatBase}`, built lazily from the registry on first use.

- Unknown goat → `404 {"error": "Goat '<name>' not found"}`.
- Goat exists in the registry but cannot be opened (missing driver, unreachable service,
  unwritable path) → `400`/`500` with the underlying reason, as `set_active_goat` reports today.
- The cache entry is dropped on `DELETE /api/goats/<name>` and the whole cache is cleared on
  `POST /api/registry`.
- `memory` goats live in the cache, so their contents last until the process restarts (unchanged
  behaviour, now per goat rather than for one global instance).

`routes.py` receives its resolver by dependency injection (`init_routes(app, resolve_goat)`)
instead of `import mojogoatapi`. This removes the module-identity split structurally:
`set_active_goat_ref`, `get_active_goat`, `requires_active_goat` and the `mojogoatapi.active_goat`
global are deleted, not patched.

### 4. Registry file

- The `active` and `default` fields are removed. On load they are ignored; the next save drops them.
- `POST /api/goats` no longer accepts `make_active` or `make_default`. Sending either returns
  `400 {"error": "make_active/make_default were removed in API v2 (ADR-016)"}`.
- `goatpath` uniqueness checks for text goats are unchanged.
- If `POST /api/goats` names an existing goat (409), clients that supplied a `goat_path` should
  compare it with the existing entry's `goatpath` via `GET /api/goats/<name>`; MojoGOAT does not
  rewrite the path of an existing goat.

### 5. `/api/status` and `/health`

- `/api/status`: drop `active_goat` and `goats[].is_active` / `is_default`; add `api_version`.
  Backend availability (`backends`) and the endpoint index (`operations`) stay.
- `/health`: drop `active_goat`; keep `status` and `goat_count`.

### 6. Operations (ADR-012 / ADR-014)

Operations are scoped to a goat.

- Each operation record gains a `goat` field, set from the URL on creation.
- Operation IDs stay globally unique, but an operation is only reachable under its own goat:
  `GET /api/goats/B/operations/<id>` for an operation created under goat A returns `404`.
  `GET /api/goats/<goat>/operations` lists only that goat's operations.
- Accepted results are applied to the goat in the URL.
- Persisted operation files from before this change have no `goat` field. `load_persisted()`
  **skips them with a warning and leaves them on disk**; nothing is deleted or migrated automatically.

### 7. Concurrency

TextGoat has per-`goatpath` write locks (`_REL_WRITE_LOCKS`), intended so that writes to
different goats never block each other and writes to one goat stay ordered. **They do not hold up
under concurrent requests, and this is independent of this ADR.** Measured 2026-11-01 with raw
HTTP against the committed v1 server (`e1ed213`) and the v2 server, with nodes pre-created: N
concurrent `POST …/relationships` to one text goat gave one `201`, `400`s for the rest, and one
request that hung until the client timed out, for both N=3 and N=12; v1 and v2 behaved
identically. Concurrent node creates (N=12) all succeeded. The cause is not investigated here;
it is tracked as ISSUE-21.

Consequence for this ADR: a goat must have **a single writer issuing writes one at a time**.
That is how Xetrapal behaves (its only `asyncio.create_task` is the CLI input loop, and graph
writes are awaited sequentially), so the two-goat target deployment is not affected. Scoping goats
by URL neither causes nor fixes the problem.

### 8. Goat names are validated

Goat names are now URL path segments, and `POST /api/goats` derives a text goat's default
directory with `os.path.join(DEFAULT_DATA_DIR, name)`. `create_goat` as read on 2026-10-31 showed
no validation of `name`, so a name such as `../x` could resolve outside the data directory. The
scoped routes make the name a more exposed input, so:

- A goat name must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`. `POST /api/goats` returns
  `400 {"error": "Invalid goat name …"}` otherwise. Existing names in use (`xpal-test`, `AVXpal`,
  `AVGFGoat`, `xpal1goat`) all match.
- For a text goat whose path is derived (no explicit `goat_path`), the resolved real path must
  lie inside `DEFAULT_DATA_DIR`; otherwise `400`.
- An explicit `goat_path` is the caller's choice (this is how `/xpal-data-remote/AVGFGoat` is
  used) and is not confined to `DEFAULT_DATA_DIR`, but it must be an absolute path.
- A registry entry whose name does not match the pattern is not reachable through the scoped
  routes (`404`). The server logs a warning at startup listing any such entries; it does not rename
  or delete them.
- This validation is not authentication. Any client can still address any goat (ISSUE-7).

## Consequences

**Positive**
- No server-wide mutable selection: parallel clients on different goats cannot interfere.
- The module-identity bug class is removed structurally rather than worked around.
- Every request is self-describing, which makes logs, tests and the OpenAPI spec (ISSUE-4)
  straightforward.
- Multi-goat reads (ISSUE-10) become a client concern: call two scoped routes.

**Negative / breaking**
- **Every existing client breaks.** Known clients: `mojogoat-ui` (uses `/api/active-goat`,
  `/api/active-goat/taxonomy`, `/api/graph`, `/api/nodes`, `/api/relationships`, `/api/operations`;
  see ISSUE-19), Xetrapal's `MojoGoatSmritiGraph` and management client (see xetrapal3 ADR-028),
  `samples/` scripts, the Postman collection, `tests/test_api*.py`, `run_api_cli_tests.sh`,
  `API_README.md` and `API_TEST_README.md` (see ISSUE-20).
- Registry files written by v0.4.0 and later lose `active`/`default`. Rolling back to v0.3.x
  would start with no active goat until one is set by hand.

**Neutral**
- The quad model, backend interface, ADR-008 (no application deletes) and the per-backend storage
  formats are untouched.

## Implementation checklist
Tracked in `tasks/todo.md` ("v0.4.0 — Goat-scoped API") and ISSUE-18 to ISSUE-21 in
`tasks/pending-issues.md`.
