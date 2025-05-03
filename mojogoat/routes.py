from flask import Flask, request, jsonify
import json
from datetime import datetime
from mojogoat.goatbases.mongogoat.models import sqldb, Relationship, Node
from mojogoatapi import app, active_goat

# API Routes for CRUD operations on the active goat

# Check if active goat is selected
def check_active_goat():
    if not active_goat:
        return jsonify({"error": "No active goat selected"}), 404
    return None

# Node Operations
@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get all nodes from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        nodes = active_goat.get_nodes()
        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get nodes: {str(e)}"}), 500

@app.route('/api/nodes/<nodeid>', methods=['GET'])
def get_node(nodeid):
    """Get a node by ID from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        node = active_goat.get_node(nodeid)
        if not node:
            return jsonify({"error": f"Node with ID '{nodeid}' not found"}), 404
        return jsonify(node), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get node: {str(e)}"}), 500

@app.route('/api/nodes/label/<label>', methods=['GET'])
def get_nodes_by_label(label):
    """Get nodes by label from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        nodes = active_goat.get_nodes_by_label(label)
        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get nodes by label: {str(e)}"}), 500

@app.route('/api/nodes', methods=['POST'])
def add_node():
    """Add a node to the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    data = request.json
    if not data or not data.get("nodeid"):
        return jsonify({"error": "Missing required field: nodeid"}), 400
    
    try:
        node = active_goat.add_node(data.get("nodeid"), **data)
        return jsonify(node), 201
    except Exception as e:
        return jsonify({"error": f"Failed to add node: {str(e)}"}), 500

@app.route('/api/nodes/<nodeid>', methods=['PUT'])
def update_node(nodeid):
    """Update a node in the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    data = request.json
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    try:
        node = active_goat.add_node(nodeid, **data)
        return jsonify(node), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update node: {str(e)}"}), 500

@app.route('/api/nodes/<nodeid>', methods=['DELETE'])
def delete_node(nodeid):
    """Delete a node from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        if active_goat.delete_node(nodeid):
            return jsonify({"message": f"Node '{nodeid}' deleted successfully"}), 200
        else:
            return jsonify({"error": f"Node with ID '{nodeid}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete node: {str(e)}"}), 500

# Relationship Operations
@app.route('/api/relationships', methods=['GET'])
def get_relationships():
    """Get relationships from the active goat with optional filtering"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    source = request.args.get('source')
    target = request.args.get('target')
    story = request.args.get('story')
    
    try:
        relationships = active_goat.get_relationships(source, target, story)
        return jsonify(relationships), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get relationships: {str(e)}"}), 500

@app.route('/api/relationships', methods=['POST'])
def create_relationship():
    """Create a relationship in the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    data = request.json
    if not data or not data.get("source") or not data.get("target") or not data.get("story"):
        return jsonify({"error": "Missing required fields: source, target, and story"}), 400
    
    try:
        relationship = active_goat.create_relationship(
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
def get_relationship(relationship_id):
    """Get a relationship by ID from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        relationships = active_goat.get_relationships()
        
        # Find relationship by ID
        for rel in relationships:
            if str(rel.get("relationship_id")) == str(relationship_id):
                return jsonify(rel), 200
        
        return jsonify({"error": f"Relationship with ID '{relationship_id}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get relationship: {str(e)}"}), 500

@app.route('/api/relationships/<relationship_id>', methods=['DELETE'])
def delete_relationship(relationship_id):
    """Delete a relationship from the active goat"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        if active_goat.delete_relationship(relationship_id):
            return jsonify({"message": f"Relationship '{relationship_id}' deleted successfully"}), 200
        else:
            return jsonify({"error": f"Relationship with ID '{relationship_id}' not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete relationship: {str(e)}"}), 500

# Additional Goat Operations
@app.route('/api/active-goat/composition', methods=['GET'])
def get_composition():
    """Get the composition of nodes by label"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        composition = active_goat.get_composition()
        return jsonify(composition), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get composition: {str(e)}"}), 500

@app.route('/api/active-goat/taxonomy', methods=['GET'])
def get_taxonomy():
    """Get the taxonomy of relationship types"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    try:
        taxonomy = active_goat.get_taxonomy()
        return jsonify(taxonomy), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get taxonomy: {str(e)}"}), 500

@app.route('/api/active-goat/dump-relationships', methods=['POST'])
def dump_relationships():
    """Dump all relationships to a file"""
    error_response = check_active_goat()
    if error_response:
        return error_response
    
    data = request.json
    if not data or not data.get("filename"):
        return jsonify({"error": "Missing required field: filename"}), 400
    
    try:
        count = active_goat.dump_all_rels(data.get("filename"))
        return jsonify({
            "message": f"Successfully dumped {count} relationships to {data.get('filename')}"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to dump relationships: {str(e)}"}), 500

