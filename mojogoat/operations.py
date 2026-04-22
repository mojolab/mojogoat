import copy
from datetime import datetime
from uuid import uuid4

_store: dict[str, dict] = {}


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
            return copy.deepcopy(op)
    return None


def delete_operation(op_id: str) -> bool:
    if op_id in _store:
        del _store[op_id]
        return True
    return False


def reset_store() -> None:
    """Clear all operations. For testing only."""
    _store.clear()
