from flask import request, jsonify
import json
from datetime import datetime
from functools import wraps


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

    # Relationship Operations

    @app.route('/api/relationships', methods=['GET'])
    @requires_active_goat
    async def get_relationships():
        source = request.args.get('source')
        target = request.args.get('target')
        story = request.args.get('story')
        limit_str = request.args.get('limit')
        limit = int(limit_str) if limit_str is not None else None
        # Any remaining query params are treated as props filters
        _reserved = {'source', 'target', 'story', 'limit'}
        props = {k: v for k, v in request.args.items() if k not in _reserved} or None
        try:
            rels = await get_active_goat().get_relationships(
                source, target, story, props=props, limit=limit
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

    # Goat-level operations

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
