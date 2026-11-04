import copy
import json
import logging
import os
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)

_store: dict[str, dict] = {}


def _operations_dir() -> str:
    """Directory operations are persisted to, so an awaiting-validation
    proposal survives a server restart (see docs/decisions/ADR-014). Read fresh from
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
    Call once at process startup. Returns the number of operations loaded.

    Operations are scoped to a goat (ADR-016). Files written before that change have no
    ``goat`` field; they are skipped with a warning and left on disk untouched.
    """
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
        if not op_id:
            continue
        if not op.get("goat"):
            logger.warning(
                "Skipping persisted operation %s: no 'goat' field (written before ADR-016); "
                "left on disk", filename)
            continue
        if op_id not in _store:
            _store[op_id] = op
            loaded += 1
    return loaded


def _visible(op: dict | None, goat: str | None) -> bool:
    """True if *op* exists and belongs to *goat* (``goat=None`` means unscoped, internal use)."""
    return op is not None and (goat is None or op.get('goat') == goat)


def create_operation(name: str, node_ids: list[str], params: dict, goat: str | None = None) -> dict:
    op_id = str(uuid4())
    now = datetime.now().isoformat()
    op: dict = {
        'operation_id': op_id,
        'goat': goat,
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


def list_operations(goat: str | None = None) -> list[dict]:
    """Operations belonging to *goat*, oldest first."""
    ops = [op for op in _store.values() if _visible(op, goat)]
    ops.sort(key=lambda o: o['created'])
    return copy.deepcopy(ops)


def get_operation(op_id: str, goat: str | None = None) -> dict | None:
    op = _store.get(op_id)
    return copy.deepcopy(op) if _visible(op, goat) else None


def post_results(op_id: str, results: list[dict], goat: str | None = None) -> dict | None:
    op = _store.get(op_id)
    if not _visible(op, goat):
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


def validate_result(op_id: str, result_id: str, action: str, goat: str | None = None) -> dict | None:
    """Set a result's status to 'accepted' or 'rejected'. Returns updated op, or None."""
    op = _store.get(op_id)
    if not _visible(op, goat):
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


def delete_operation(op_id: str, goat: str | None = None) -> bool:
    if _visible(_store.get(op_id), goat):
        del _store[op_id]
        _remove_persisted(op_id)
        return True
    return False


def reset_store() -> None:
    """Clear all operations. For testing only."""
    _store.clear()
