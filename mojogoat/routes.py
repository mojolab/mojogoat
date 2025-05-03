from flask import Flask, request, jsonify, current_app
import json
from datetime import datetime
from functools import wraps
from mojogoat.goatbases.mongogoat.models import sqldb, Relationship, Node

# Initialize the routes module
def init_routes(app):
    """Initialize the routes with the Flask app"""
    register_routes(app)

# API Routes for CRUD operations on the active goat

# Module level active_goat reference
_active_goat = None

def set_active_goat_ref(goat):
    """Set the active goat reference for routes"""
    global _active_goat
    _active_goat = goat
    
def get_active_goat():
    """Get active goat from the module"""
    global _active_goat
    
    # If not set in the module, try to import from mojogoatapi
    if _active_goat is None:
        try:
            from mojogoatapi import active_goat
            _active_goat = active_goat
        except (ImportError, AttributeError) as e:
            print(f"Error getting active goat: {e}")
    
    return _active_goat

# Check if active goat is selected
def check_active_goat():
    active_goat = get_active_goat()
    
    # For debugging
    import sys
    print(f"check_active_goat called, active_goat is: {active_goat}", file=sys.stderr)
    
    if not active_goat:
        # Try to get active goat from mojogoatapi again, in case it was set after initialization
        try:
            from mojogoatapi import active_goat as mojo_active_goat
            if mojo_active_goat:
                # Update our local reference
                set_active_goat_ref(mojo_active_goat)
                return None
        except Exception as e:
            print(f"Error trying to get active_goat from mojogoatapi: {e}", file=sys.stderr)
            
        return jsonify({"error": "No active goat selected"}), 404
    return None
    
# Decorator to ensure an active goat is selected
def requires_active_goat(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        error_response = check_active_goat()
        if error_response:
            return error_response
        return f(*args, **kwargs)
    return decorated_function

# Reference to the Flask app
_app = None

# Node Operations
def register_routes(app):
    """Register all routes with the Flask app"""
    global _app
    _app = app
    
    @app.route('/api/nodes', methods=['GET'])
    @requires_active_goat
    def get_nodes():
        """Get all nodes from the active goat"""
        try:
            nodes = get_active_goat().get_nodes()
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['GET'])
    @requires_active_goat
    def get_node(nodeid):
        """Get a node by ID from the active goat"""
        try:
            node = get_active_goat().get_node(nodeid)
            if not node:
                return jsonify({"error": f"Node with ID '{nodeid}' not found"}), 404
            return jsonify(node), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get node: {str(e)}"}), 500

    @app.route('/api/nodes/label/<label>', methods=['GET'])
    @requires_active_goat
    def get_nodes_by_label(label):
        """Get nodes by label from the active goat"""
        try:
            nodes = get_active_goat().get_nodes_by_label(label)
            return jsonify(nodes), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get nodes by label: {str(e)}"}), 500

    @app.route('/api/nodes', methods=['POST'])
    @requires_active_goat
    def add_node():
        """Add a node to the active goat"""
        data = request.json
        if not data or not data.get("nodeid"):
            return jsonify({"error": "Missing required field: nodeid"}), 400
        
        try:
            # Create a copy of the data to avoid modifying the original
            node_data = dict(data)
            nodeid = node_data.pop("nodeid")
            
            # Pass nodeid separately and the rest as kwargs
            node = get_active_goat().add_node(nodeid, **node_data)
            return jsonify(node), 201
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to add node: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['PUT'])
    @requires_active_goat
    def update_node(nodeid):
        """Update a node in the active goat"""
        data = request.json
        if not data:
            return jsonify({"error": "No update data provided"}), 400
        
        try:
            # Ensure we're not passing nodeid in kwargs
            node_data = dict(data)
            if "nodeid" in node_data:
                del node_data["nodeid"]
                
            # Add nodeid to the data for consistent identification
            node_data["nodeid"] = nodeid
            
            # Update the node
            node = get_active_goat().add_node(nodeid, **node_data)
            return jsonify(node), 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to update node: {str(e)}"}), 500

    @app.route('/api/nodes/<nodeid>', methods=['DELETE'])
    @requires_active_goat
    def delete_node(nodeid):
        """Delete a node from the active goat"""
        try:
            if get_active_goat().delete_node(nodeid):
                return jsonify({"message": f"Node '{nodeid}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Node with ID '{nodeid}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete node: {str(e)}"}), 500

    # Relationship Operations
    @app.route('/api/relationships', methods=['GET'])
    @requires_active_goat
    def get_relationships():
        """Get relationships from the active goat with optional filtering"""
        source = request.args.get('source')
        target = request.args.get('target')
        story = request.args.get('story')
        
        try:
            relationships = get_active_goat().get_relationships(source, target, story)
            return jsonify(relationships), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get relationships: {str(e)}"}), 500

    @app.route('/api/relationships', methods=['POST'])
    @requires_active_goat
    def create_relationship():
        """Create a relationship in the active goat"""
        data = request.json
        if not data or not data.get("source") or not data.get("target") or not data.get("story"):
            return jsonify({"error": "Missing required fields: source, target, and story"}), 400
        
        try:
            relationship = get_active_goat().create_relationship(
                data.get("source"),
                data.get("target"),
                data.get("story")
            )
            
            if not relationship:
                return jsonify({"error": "Failed to create relationship. Nodes may not exist."}), 400
            
            return jsonify(relationship), 201
        except Exception as e:
            return jsonify({"error": f"Failed to create relationship: {str(e)}"}), 500

    @app.route('/api/relationships/<relationship_id>', methods=['GET'])
    @requires_active_goat
    def get_relationship(relationship_id):
        """Get a relationship by ID from the active goat"""
        try:
            relationships = get_active_goat().get_relationships()
            
            # Find relationship by ID
            for rel in relationships:
                if str(rel.get("relationship_id")) == str(relationship_id):
                    return jsonify(rel), 200
            
            return jsonify({"error": f"Relationship with ID '{relationship_id}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to get relationship: {str(e)}"}), 500

    @app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
    @requires_active_goat
    def delete_relationship(relationship_id):
        """Delete a relationship from the active goat"""
        try:
            if get_active_goat().delete_relationship(relationship_id):
                return jsonify({"message": f"Relationship '{relationship_id}' deleted successfully"}), 200
            else:
                return jsonify({"error": f"Relationship with ID '{relationship_id}' not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete relationship: {str(e)}"}), 500

    # Additional Goat Operations
    @app.route('/api/active-goat/composition', methods=['GET'])
    @requires_active_goat
    def get_composition():
        """Get the composition of nodes by label"""
        try:
            composition = get_active_goat().get_composition()
            return jsonify(composition), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get composition: {str(e)}"}), 500

    @app.route('/api/active-goat/taxonomy', methods=['GET'])
    @requires_active_goat
    def get_taxonomy():
        """Get the taxonomy of relationship types"""
        try:
            taxonomy = get_active_goat().get_taxonomy()
            return jsonify(taxonomy), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get taxonomy: {str(e)}"}), 500

    @app.route('/api/active-goat/dump-relationships', methods=['POST'])
    @requires_active_goat
    def dump_relationships():
        """Dump all relationships to a file"""
        data = request.json
        if not data or not data.get("filename"):
            return jsonify({"error": "Missing required field: filename"}), 400
        
        try:
            count = get_active_goat().dump_all_rels(data.get("filename"))
            return jsonify({
                "message": f"Successfully dumped {count} relationships to {data.get('filename')}"
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to dump relationships: {str(e)}"}), 500

