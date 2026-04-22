import asyncio
import os
import json
import aiofiles
from flask import request, jsonify
from datetime import datetime
from functools import wraps

from mojogoat import operations as ops_module


def init_routes(app):
    """Initialize the routes with the Flask app."""
    register_routes(app)


def set_active_goat_ref(goat):
    """Set the active goat in mojogoatapi. Kept for test-teardown compatibility."""
    try:
        import mojogoatapi
        mojogoatapi.active_goat = goat
    except (ImportError, AttributeError):
        pass


def get_active_goat():
    """Return the current active GoatBase instance from mojogoatapi."""
    try:
        import mojogoatapi
        return mojogoatapi.active_goat
    except (ImportError, AttributeError):
        return None


def check_active_goat():
    if not get_active_goat():
        return jsonify({"error": "No active goat selected"}), 404
    return None


def requires_active_goat(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        error_response = check_active_goat()
        if error_response:
            return error_response
        return await f(*args, **kwargs)
    return decorated_function


_app = None


def register_routes(app):
    global _app
    _app = app

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    @app.route('/api/nodes', methods=['GET'])
    @requires_active_goat
    async def get_nodes():
        try:
            nodes = await get_active_goat().get_nodes()
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['GET'])
    @requires_active_goat
    async def get_node(nodeid):
        try:
            node = await get_active_goat().get_node(nodeid)
            if not node:
                return jsonify({"error": f"Node '{nodeid}' not found"}), 404
            return jsonify(node), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get node: {str(e)}"}), 500

    @app.route('/api/nodes/label/<label>', methods=['GET'])
    @requires_active_goat
    async def get_nodes_by_label(label):
        try:
            nodes = await get_active_goat().get_nodes_by_label(label)
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes by label: {str(e)}"}), 500

    @app.route('/api/nodes', methods=['POST'])
    @requires_active_goat
    async def add_node():
        data = request.json
        if not data or not data.get("nodeid"):
            return jsonify({"error": "Missing required field: nodeid"}), 400
        nodeid_raw = data.get("nodeid", "")
        if '/' in nodeid_raw:
            return jsonify({
                "error": f"nodeid must not contain '/'. Use percent-encoding (e.g. '%2F') for literal slashes."
            }), 400
        try:
            node_data = dict(data)
            nodeid = node_data.pop("nodeid")
            node = await get_active_goat().add_node(nodeid, **node_data)
            return jsonify(node), 201
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to add node: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['PUT'])
    @requires_active_goat
    async def update_node(nodeid):
        data = request.json
        if not data:
            return jsonify({"error": "No update data provided"}), 400
        try:
            node_data = {k: v for k, v in data.items() if k != "nodeid"}
            node = await get_active_goat().add_node(nodeid, **node_data)
            return jsonify(node), 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to update node: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['DELETE'])
    @requires_active_goat
    async def delete_node(nodeid):
        try:
            if await get_active_goat().delete_node(nodeid):
                return jsonify({"message": f"Node '{nodeid}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Node '{nodeid}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete node: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    @app.route('/api/relationships', methods=['GET'])
    @requires_active_goat
    async def get_relationships():
        source = request.args.get('source')
        target = request.args.get('target')
        story = request.args.get('story')
        limit_str = request.args.get('limit')
        offset_str = request.args.get('offset')
        limit = int(limit_str) if limit_str is not None else None
        offset = int(offset_str) if offset_str is not None else None
        _reserved = {'source', 'target', 'story', 'limit', 'offset'}
        props = {k: v for k, v in request.args.items() if k not in _reserved} or None
        try:
            rels = await get_active_goat().get_relationships(
                source, target, story, props=props, limit=limit, offset=offset
            )
            return jsonify(rels), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get relationships: {str(e)}"}), 500

    @app.route('/api/relationships', methods=['POST'])
    @requires_active_goat
    async def create_relationship():
        data = request.json
        if not data or not data.get("source") or not data.get("target") or not data.get("story"):
            return jsonify({"error": "Missing required fields: source, target, and story"}), 400
        try:
            extra = {k: v for k, v in data.items() if k not in ("source", "target", "story")}
            rel = await get_active_goat().create_relationship(
                data["source"], data["target"], data["story"], **extra
            )
            if not rel:
                return jsonify({"error": "Failed to create relationship. Nodes may not exist."}), 400
            return jsonify(rel), 201
        except Exception as e:
            return jsonify({"error": f"Failed to create relationship: {str(e)}"}), 500

    @app.route('/api/relationships/<relationship_id>', methods=['GET'])
    @requires_active_goat
    async def get_relationship(relationship_id):
        try:
            rel = await get_active_goat().get_relationship(relationship_id)
            if rel is None:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
            return jsonify(rel), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get relationship: {str(e)}"}), 500

    @app.route('/api/relationships/<relationship_id>', methods=['PATCH'])
    @requires_active_goat
    async def update_relationship(relationship_id):
        data = request.json or {}
        try:
            ok = await get_active_goat().update_relationship_props(relationship_id, **data)
            if not ok:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
            return jsonify({"message": "Updated", "relationship_id": relationship_id}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to update relationship: {str(e)}"}), 500

    @app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
    @requires_active_goat
    async def delete_relationship(relationship_id):
        try:
            if await get_active_goat().delete_relationship(relationship_id):
                return jsonify({"message": f"Relationship '{relationship_id}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete relationship: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Goat-level analytics / utility
    # ------------------------------------------------------------------

    @app.route('/api/active-goat/composition', methods=['GET'])
    @requires_active_goat
    async def get_composition():
        try:
            composition = await get_active_goat().get_composition()
            return jsonify(composition), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get composition: {str(e)}"}), 500

    @app.route('/api/active-goat/taxonomy', methods=['GET'])
    @requires_active_goat
    async def get_taxonomy():
        try:
            taxonomy = await get_active_goat().get_taxonomy()
            return jsonify(taxonomy), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get taxonomy: {str(e)}"}), 500

    @app.route('/api/active-goat/dump-relationships', methods=['POST'])
    @requires_active_goat
    async def dump_relationships():
        data = request.json
        if not data or not data.get("filename"):
            return jsonify({"error": "Missing required field: filename"}), 400
        try:
            count = await get_active_goat().dump_all_rels(data["filename"])
            return jsonify({
                "message": f"Successfully dumped {count} relationships to {data['filename']}"
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to dump relationships: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Item 14 — TextGoat snapshot compaction (ADR-0007)
    # ------------------------------------------------------------------

    @app.route('/api/active-goat/compact', methods=['POST'])
    @requires_active_goat
    async def compact_goat():
        goat = get_active_goat()
        if not hasattr(goat, 'compact'):
            return jsonify({'error': 'compact is only supported for text goats'}), 400
        try:
            count = await goat.compact()
            return jsonify({'message': f'Compacted. {count} relationships preserved.', 'relationship_count': count}), 200
        except Exception as e:
            return jsonify({'error': f'Compaction failed: {str(e)}'}), 500

    # ------------------------------------------------------------------
    # Item 15 — Bulk import (inverse of dump-relationships)
    # ------------------------------------------------------------------

    @app.route('/api/active-goat/import-relationships', methods=['POST'])
    @requires_active_goat
    async def import_relationships():
        data = request.json or {}
        filename = data.get('filename')
        if not filename:
            return jsonify({'error': 'Missing required field: filename'}), 400
        if not os.path.exists(filename):
            return jsonify({'error': f'File not found: {filename}'}), 400

        imported = 0
        skipped = 0
        errors: list[str] = []
        goat = get_active_goat()

        try:
            async with aiofiles.open(filename, 'r') as f:
                content = await f.read()
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 500

        lines = [ln.strip() for ln in content.split('\n') if ln.strip()]
        for line_num, line in enumerate(lines, 1):
            parts = line.split('|')
            if len(parts) < 3:
                skipped += 1
                errors.append(f'Line {line_num}: too few fields, skipped')
                continue
            source, story, target = parts[0], parts[1], parts[2]
            extra: dict = {}
            if len(parts) >= 6:
                try:
                    extra = json.loads(parts[5])
                except (json.JSONDecodeError, ValueError):
                    pass
            try:
                if not await goat.get_node(source):
                    await goat.add_node(source)
                if not await goat.get_node(target):
                    await goat.add_node(target)
                rel = await goat.create_relationship(source, target, story, **extra)
                if rel:
                    imported += 1
                else:
                    skipped += 1
                    errors.append(f'Line {line_num}: create_relationship returned None')
            except Exception as e:
                skipped += 1
                errors.append(f'Line {line_num}: {str(e)}')

        return jsonify({'imported': imported, 'skipped': skipped, 'errors': errors}), 200

    # ------------------------------------------------------------------
    # Item 12 — Graph data API (ADR-0011)
    # ------------------------------------------------------------------

    @app.route('/api/graph', methods=['GET'])
    @requires_active_goat
    async def get_graph():
        source = request.args.get('source')
        target = request.args.get('target')
        story = request.args.get('story')
        limit_str = request.args.get('limit')
        node_ids_str = request.args.get('node_ids')
        limit = int(limit_str) if limit_str is not None else None
        requested_node_ids = set(node_ids_str.split(',')) if node_ids_str else None

        _reserved = {'source', 'target', 'story', 'limit', 'node_ids'}
        props = {k: v for k, v in request.args.items() if k not in _reserved} or None

        try:
            goat = get_active_goat()
            all_nodes, edges = await asyncio.gather(
                goat.get_nodes(),
                goat.get_relationships(source, target, story, props=props, limit=limit),
            )

            node_map = {n['nodeid']: n for n in all_nodes}

            # node_ids: restrict edges to those entirely within the requested subgraph
            if requested_node_ids is not None:
                edges = [
                    e for e in edges
                    if e['source_id'] in requested_node_ids and e['target_id'] in requested_node_ids
                ]

            # Include nodes referenced by returned edges + any explicitly requested
            referenced = {e['source_id'] for e in edges} | {e['target_id'] for e in edges}
            include_ids = referenced | (requested_node_ids or set())
            nodes = [node_map[nid] for nid in include_ids if nid in node_map]

            return jsonify({
                'nodes': nodes,
                'edges': edges,
                'node_count': len(nodes),
                'edge_count': len(edges),
            }), 200
        except Exception as e:
            return jsonify({'error': f'Failed to get graph: {str(e)}'}), 500

    # ------------------------------------------------------------------
    # Item 13 — Operations API (ADR-0012)
    # ------------------------------------------------------------------

    @app.route('/api/operations', methods=['POST'])
    def create_operation():
        data = request.json or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Missing required field: name'}), 400
        node_ids = data.get('node_ids', [])
        params = data.get('params', {})
        op = ops_module.create_operation(name, node_ids, params)
        return jsonify(op), 201

    @app.route('/api/operations/<op_id>', methods=['GET'])
    def get_operation(op_id):
        op = ops_module.get_operation(op_id)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404
        return jsonify(op), 200

    @app.route('/api/operations/<op_id>/results', methods=['POST'])
    def post_operation_results(op_id):
        data = request.json or {}
        results = data.get('results', [])
        if not isinstance(results, list):
            return jsonify({'error': 'results must be a list'}), 400
        op = ops_module.post_results(op_id, results)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404
        return jsonify(op), 200

    @app.route('/api/operations/<op_id>/validate', methods=['POST'])
    @requires_active_goat
    async def validate_operation_result(op_id):
        data = request.json or {}
        result_id = data.get('result_id')
        action = data.get('action')

        if not result_id or action not in ('accept', 'reject'):
            return jsonify({'error': "Missing required fields: result_id, action ('accept'|'reject')"}), 400

        op = ops_module.get_operation(op_id)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404

        result = next((r for r in op['results'] if r.get('result_id') == result_id), None)
        if result is None:
            return jsonify({'error': f'Result {result_id} not found'}), 404
        if result['status'] != 'proposed':
            return jsonify({'error': f'Result is already {result["status"]}'}), 400

        if action == 'accept':
            goat = get_active_goat()
            payload = dict(result.get('payload', {}))
            result_type = result.get('type')
            try:
                if result_type == 'add_node':
                    nodeid = payload.pop('nodeid')
                    await goat.add_node(nodeid, **payload)
                elif result_type == 'add_relationship':
                    src = payload.pop('source')
                    tgt = payload.pop('target')
                    sty = payload.pop('story')
                    if not await goat.get_node(src):
                        await goat.add_node(src)
                    if not await goat.get_node(tgt):
                        await goat.add_node(tgt)
                    await goat.create_relationship(src, tgt, sty, **payload)
                elif result_type == 'update_node':
                    nodeid = payload.pop('nodeid')
                    await goat.add_node(nodeid, **payload)
                elif result_type == 'update_relationship':
                    rel_id = payload.pop('relationship_id')
                    await goat.update_relationship_props(rel_id, **payload)
                else:
                    return jsonify({'error': f'Unknown result type: {result_type}'}), 400
            except Exception as e:
                return jsonify({'error': f'Failed to execute write for result {result_id}: {str(e)}'}), 500

        updated = ops_module.validate_result(op_id, result_id, action)
        return jsonify(updated), 200

    @app.route('/api/operations/<op_id>', methods=['DELETE'])
    def delete_operation(op_id):
        if ops_module.delete_operation(op_id):
            return jsonify({'message': f'Operation {op_id} deleted'}), 200
        return jsonify({'error': f'Operation {op_id} not found'}), 404
