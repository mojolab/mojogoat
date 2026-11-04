"""Goat-scoped REST routes (ADR-016).

There is no "active goat": every data route names its goat in the URL
(``/api/goats/<goat>/...``) and the goat is resolved per request through the
``resolve_goat`` callable handed to :func:`init_routes`. Removed v1 routes return
``410 Gone`` naming their replacement.
"""
import asyncio
import os
import json
import aiofiles
from flask import request, jsonify
from functools import wraps

from mojogoat import operations as ops_module
from mojogoat.errors import GoatNotFound, GoatUnavailable

API_VERSION = 2


def init_routes(app, resolve_goat):
    """Register all goat-scoped routes and the 410 stubs for removed v1 routes.

    ``resolve_goat(name)`` returns a GoatBase or raises GoatNotFound / GoatUnavailable.
    """
    register_routes(app, resolve_goat)
    register_gone_stubs(app)


# ----------------------------------------------------------------------
# 410 Gone stubs for routes removed in API v2
# ----------------------------------------------------------------------

_ALL_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']


def _gone(replacement: str):
    return jsonify({
        "error": f"Removed in API v2 (ADR-016): {replacement}",
        "api_version": API_VERSION,
    }), 410


def register_gone_stubs(app):
    def add(rule, replacement, methods=None, endpoint=None):
        def view(**kwargs):
            repl = replacement
            if '{rest}' in repl:
                repl = repl.replace('{rest}', kwargs.get('rest', ''))
            return _gone(repl)
        app.add_url_rule(rule, endpoint or f"gone:{rule}", view, methods=methods or _ALL_METHODS)

    add('/api/active-goat', 'there is no active goat; use GET /api/goats/<name>', ['GET', 'POST'])
    add('/api/active-goat/<path:rest>', 'use /api/goats/<goat>/{rest}')
    add('/api/backend', 'create a goat with POST /api/goats (type text|memory|...)', ['GET', 'POST'])
    add('/api/direct/nodes', 'use GET /api/goats/<goat>/nodes', ['GET'])
    add('/api/debug', 'no replacement', ['GET'])
    for prefix in ('nodes', 'relationships', 'operations'):
        add(f'/api/{prefix}', f'use /api/goats/<goat>/{prefix}')
        add(f'/api/{prefix}/<path:rest>', f'use /api/goats/<goat>/{prefix}/{{rest}}')
    add('/api/graph', 'use GET /api/goats/<goat>/graph', ['GET'])


# ----------------------------------------------------------------------
# Goat-scoped routes
# ----------------------------------------------------------------------

def _scoped(resolve_goat):
    """Decorator factory: resolve ``<goat>`` from the URL and pass the instance to the view.

    The wrapped view is called as ``view(goat_instance, goat_name, **other_url_args)``.
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(goat, **kwargs):
            try:
                instance = resolve_goat(goat)
            except GoatNotFound:
                return jsonify({"error": f"Goat '{goat}' not found"}), 404
            except GoatUnavailable as e:
                return jsonify({"error": str(e)}), 400
            return await f(instance, goat, **kwargs)
        return wrapper
    return decorator


def register_routes(app, resolve_goat):
    scoped = _scoped(resolve_goat)
    base = '/api/goats/<goat>'

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    @app.route(f'{base}/nodes', methods=['GET'])
    @scoped
    async def get_nodes(g, goat):
        try:
            nodes = await g.get_nodes()
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes: {str(e)}"}), 500

    @app.route(f'{base}/nodes/<nodeid>', methods=['GET'])
    @scoped
    async def get_node(g, goat, nodeid):
        try:
            node = await g.get_node(nodeid)
            if not node:
                return jsonify({"error": f"Node '{nodeid}' not found"}), 404
            return jsonify(node), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get node: {str(e)}"}), 500

    @app.route(f'{base}/nodes/label/<label>', methods=['GET'])
    @scoped
    async def get_nodes_by_label(g, goat, label):
        try:
            nodes = await g.get_nodes_by_label(label)
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes by label: {str(e)}"}), 500

    @app.route(f'{base}/nodes', methods=['POST'])
    @scoped
    async def add_node(g, goat):
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
            node = await g.add_node(nodeid, **node_data)
            return jsonify(node), 201
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to add node: {str(e)}"}), 500

    @app.route(f'{base}/nodes/<nodeid>', methods=['PUT'])
    @scoped
    async def update_node(g, goat, nodeid):
        data = request.json
        if not data:
            return jsonify({"error": "No update data provided"}), 400
        try:
            node_data = {k: v for k, v in data.items() if k != "nodeid"}
            node = await g.add_node(nodeid, **node_data)
            return jsonify(node), 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to update node: {str(e)}"}), 500

    @app.route(f'{base}/nodes/<nodeid>', methods=['DELETE'])
    @scoped
    async def delete_node(g, goat, nodeid):
        try:
            if await g.delete_node(nodeid):
                return jsonify({"message": f"Node '{nodeid}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Node '{nodeid}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete node: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    @app.route(f'{base}/relationships', methods=['GET'])
    @scoped
    async def get_relationships(g, goat):
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
            rels = await g.get_relationships(
                source, target, story, props=props, limit=limit, offset=offset
            )
            return jsonify(rels), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get relationships: {str(e)}"}), 500

    @app.route(f'{base}/relationships', methods=['POST'])
    @scoped
    async def create_relationship(g, goat):
        data = request.json
        if not data or not data.get("source") or not data.get("target") or not data.get("story"):
            return jsonify({"error": "Missing required fields: source, target, and story"}), 400
        try:
            extra = {k: v for k, v in data.items() if k not in ("source", "target", "story")}
            rel = await g.create_relationship(
                data["source"], data["target"], data["story"], **extra
            )
            if not rel:
                return jsonify({"error": "Failed to create relationship. Nodes may not exist."}), 400
            return jsonify(rel), 201
        except Exception as e:
            return jsonify({"error": f"Failed to create relationship: {str(e)}"}), 500

    @app.route(f'{base}/relationships/<relationship_id>', methods=['GET'])
    @scoped
    async def get_relationship(g, goat, relationship_id):
        try:
            rel = await g.get_relationship(relationship_id)
            if rel is None:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
            return jsonify(rel), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get relationship: {str(e)}"}), 500

    @app.route(f'{base}/relationships/<relationship_id>', methods=['PATCH'])
    @scoped
    async def update_relationship(g, goat, relationship_id):
        data = request.json or {}
        try:
            ok = await g.update_relationship_props(relationship_id, **data)
            if not ok:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
            return jsonify({"message": "Updated", "relationship_id": relationship_id}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to update relationship: {str(e)}"}), 500

    @app.route(f'{base}/relationships/<relationship_id>', methods=['DELETE'])
    @scoped
    async def delete_relationship(g, goat, relationship_id):
        try:
            if await g.delete_relationship(relationship_id):
                return jsonify({"message": f"Relationship '{relationship_id}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Relationship '{relationship_id}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete relationship: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Goat-level analytics / utility
    # ------------------------------------------------------------------

    @app.route(f'{base}/composition', methods=['GET'])
    @scoped
    async def get_composition(g, goat):
        try:
            composition = await g.get_composition()
            return jsonify(composition), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get composition: {str(e)}"}), 500

    @app.route(f'{base}/taxonomy', methods=['GET'])
    @scoped
    async def get_taxonomy(g, goat):
        try:
            taxonomy = await g.get_taxonomy()
            return jsonify(taxonomy), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get taxonomy: {str(e)}"}), 500

    @app.route(f'{base}/dump-relationships', methods=['POST'])
    @scoped
    async def dump_relationships(g, goat):
        data = request.json
        if not data or not data.get("filename"):
            return jsonify({"error": "Missing required field: filename"}), 400
        try:
            count = await g.dump_all_rels(data["filename"])
            return jsonify({
                "message": f"Successfully dumped {count} relationships to {data['filename']}"
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to dump relationships: {str(e)}"}), 500

    # ------------------------------------------------------------------
    # Item 14 — TextGoat snapshot compaction (ADR-007)
    # ------------------------------------------------------------------

    @app.route(f'{base}/compact', methods=['POST'])
    @scoped
    async def compact_goat(g, goat):
        if not hasattr(g, 'compact'):
            return jsonify({'error': 'compact is only supported for text goats'}), 400
        try:
            count = await g.compact()
            return jsonify({'message': f'Compacted. {count} relationships preserved.', 'relationship_count': count}), 200
        except Exception as e:
            return jsonify({'error': f'Compaction failed: {str(e)}'}), 500

    # ------------------------------------------------------------------
    # Item 15 — Bulk import (inverse of dump-relationships)
    # ------------------------------------------------------------------

    @app.route(f'{base}/import-relationships', methods=['POST'])
    @scoped
    async def import_relationships(g, goat):
        data = request.json or {}
        filename = data.get('filename')
        if not filename:
            return jsonify({'error': 'Missing required field: filename'}), 400
        if not os.path.exists(filename):
            return jsonify({'error': f'File not found: {filename}'}), 400

        imported = 0
        skipped = 0
        errors: list[str] = []

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
                if not await g.get_node(source):
                    await g.add_node(source)
                if not await g.get_node(target):
                    await g.add_node(target)
                rel = await g.create_relationship(source, target, story, **extra)
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
    # Item 12 — Graph data API (ADR-011)
    # ------------------------------------------------------------------

    @app.route(f'{base}/graph', methods=['GET'])
    @scoped
    async def get_graph(g, goat):
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
            all_nodes, edges = await asyncio.gather(
                g.get_nodes(),
                g.get_relationships(source, target, story, props=props, limit=limit),
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
    # Item 13 — Operations API (ADR-012), scoped per goat (ADR-016 §6)
    # ------------------------------------------------------------------

    @app.route(f'{base}/operations', methods=['GET'])
    @scoped
    async def list_operations(g, goat):
        return jsonify(ops_module.list_operations(goat)), 200

    @app.route(f'{base}/operations', methods=['POST'])
    @scoped
    async def create_operation(g, goat):
        data = request.json or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Missing required field: name'}), 400
        node_ids = data.get('node_ids', [])
        params = data.get('params', {})
        op = ops_module.create_operation(name, node_ids, params, goat=goat)
        return jsonify(op), 201

    @app.route(f'{base}/operations/<op_id>', methods=['GET'])
    @scoped
    async def get_operation(g, goat, op_id):
        op = ops_module.get_operation(op_id, goat=goat)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404
        return jsonify(op), 200

    @app.route(f'{base}/operations/<op_id>/results', methods=['POST'])
    @scoped
    async def post_operation_results(g, goat, op_id):
        data = request.json or {}
        results = data.get('results', [])
        if not isinstance(results, list):
            return jsonify({'error': 'results must be a list'}), 400
        op = ops_module.post_results(op_id, results, goat=goat)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404
        return jsonify(op), 200

    @app.route(f'{base}/operations/<op_id>/validate', methods=['POST'])
    @scoped
    async def validate_operation_result(g, goat, op_id):
        data = request.json or {}
        result_id = data.get('result_id')
        action = data.get('action')

        if not result_id or action not in ('accept', 'reject'):
            return jsonify({'error': "Missing required fields: result_id, action ('accept'|'reject')"}), 400

        op = ops_module.get_operation(op_id, goat=goat)
        if op is None:
            return jsonify({'error': f'Operation {op_id} not found'}), 404

        result = next((r for r in op['results'] if r.get('result_id') == result_id), None)
        if result is None:
            return jsonify({'error': f'Result {result_id} not found'}), 404
        if result['status'] != 'proposed':
            return jsonify({'error': f'Result is already {result["status"]}'}), 400

        if action == 'accept':
            payload = dict(result.get('payload', {}))
            result_type = result.get('type')
            try:
                if result_type == 'add_node':
                    nodeid = payload.pop('nodeid')
                    await g.add_node(nodeid, **payload)
                elif result_type == 'add_relationship':
                    src = payload.pop('source')
                    tgt = payload.pop('target')
                    sty = payload.pop('story')
                    if not await g.get_node(src):
                        await g.add_node(src)
                    if not await g.get_node(tgt):
                        await g.add_node(tgt)
                    await g.create_relationship(src, tgt, sty, **payload)
                elif result_type == 'update_node':
                    nodeid = payload.pop('nodeid')
                    await g.add_node(nodeid, **payload)
                elif result_type == 'update_relationship':
                    rel_id = payload.pop('relationship_id')
                    await g.update_relationship_props(rel_id, **payload)
                else:
                    return jsonify({'error': f'Unknown result type: {result_type}'}), 400
            except Exception as e:
                return jsonify({'error': f'Failed to execute write for result {result_id}: {str(e)}'}), 500

        updated = ops_module.validate_result(op_id, result_id, action, goat=goat)
        return jsonify(updated), 200

    @app.route(f'{base}/operations/<op_id>', methods=['DELETE'])
    @scoped
    async def delete_operation(g, goat, op_id):
        if ops_module.delete_operation(op_id, goat=goat):
            return jsonify({'message': f'Operation {op_id} deleted'}), 200
        return jsonify({'error': f'Operation {op_id} not found'}), 404
