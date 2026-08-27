import copy
import json
import os
from datetime import datetime
from uuid import uuid4

_store: dict[str, dict] = {}


def _operations_dir() -> str:
    """Directory operations are persisted to, so an awaiting-validation
    proposal survives a server restart (see docs/decisions/0014). Read fresh from
    the environment on each call (not cached) so tests can override it."""
    return os.environ.get("MOJOGOAT_OPERATIONS_DIR", "/xpal-data/run/operations")


def _persist(op: dict) -> None:
    """Best-effort write-through — a persistence failure should not break
    the in-memory API, which remains the source of truth at runtime."""
    try:
        directory = _operations_dir()
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"{op['operation_id']}.json"), "w") as f:
            json.dump(op, f, indent=2)
    except OSError:
        pass


def _remove_persisted(op_id: str) -> None:
    try:
        os.remove(os.path.join(_operations_dir(), f"{op_id}.json"))
    except OSError:
        pass


def load_persisted() -> int:
    """Reload any operations persisted to disk into the in-memory store.
    Call once at process startup. Returns the number of operations loaded."""
    directory = _operations_dir()
    if not os.path.isdir(directory):
        return 0
    loaded = 0
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, filename)) as f:
                op = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        op_id = op.get("operation_id")
        if op_id and op_id not in _store:
            _store[op_id] = op
            loaded += 1
    return loaded


def create_operation(name: str, node_ids: list[str], params: dict) -> dict:
    op_id = str(uuid4())
    now = datetime.now().isoformat()
    op: dict = {
        'operation_id': op_id,
        'name': name,
        'status': 'pending',
        'node_ids': node_ids,
        'params': params,
        'results': [],
        'created': now,
        'updated': now,
    }
    _store[op_id] = op
    _persist(op)
    return copy.deepcopy(op)


def get_operation(op_id: str) -> dict | None:
    op = _store.get(op_id)
    return copy.deepcopy(op) if op else None


def post_results(op_id: str, results: list[dict]) -> dict | None:
    op = _store.get(op_id)
    if op is None:
        return None
    now = datetime.now().isoformat()
    for r in results:
        r.setdefault('result_id', str(uuid4()))
        r.setdefault('status', 'proposed')
    op['results'].extend(results)
    op['status'] = 'awaiting_validation'
    op['updated'] = now
    _persist(op)
    return copy.deepcopy(op)


def validate_result(op_id: str, result_id: str, action: str) -> dict | None:
    """Set a result's status to 'accepted' or 'rejected'. Returns updated op, or None."""
    op = _store.get(op_id)
    if op is None:
        return None
    for r in op['results']:
        if r.get('result_id') == result_id:
            r['status'] = 'accepted' if action == 'accept' else 'rejected'
            op['updated'] = datetime.now().isoformat()
            if all(res['status'] in ('accepted', 'rejected') for res in op['results']):
                op['status'] = 'completed'
            _persist(op)
            return copy.deepcopy(op)
    return None


def delete_operation(op_id: str) -> bool:
    if op_id in _store:
        del _store[op_id]
        _remove_persisted(op_id)
        return True
    return False


def reset_store() -> None:
    """Clear all operations. For testing only."""
    _store.clear()
