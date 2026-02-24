'''
MojoGOAT API - A Graph of All Things API
'''
# TODO: #1 FEATURE - Add a command to process facts as distinct from relationships
# TODO: #2 FEATURE - Add a command to process meeting notes
# TODO: #3 FEATURE - Add a command to delete new lines by message reply
# TODO: #4 OPTIMIZE - Standardize command function nomenclature and taxonomy
# TODO: #6 ARCHITECTURE - Read labels from a schema file
# TODO: #7 ARCHITECTURE - Read object schemas from a schema file
# TODO: #8 ARCHITECTURE - Use appropriate stores for appropriate data - line records for relationships and doc records on entities

import io, os, re, sys
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mongoengine import MongoEngine
from flask_cors import CORS, cross_origin

# Create Flask app
app = Flask(__name__)
CORS(app)

# Default registry location
DEFAULT_REGISTRY_PATH = os.environ.get('MOJOGOAT_REGISTRY', '/xpal-data/conf/goat_registry.json')

# Global variables for registry (need to be declared before they're used)
active_goat = None
active_goat_name = None
registry_path = None 
registry = {}

# Initialize database connections
sqldb = SQLAlchemy()
mongodb = MongoEngine()

def initialize_app(registry_file=None):
    """Initialize the application with the registry file"""
    global registry, registry_path, active_goat, active_goat_name
    
    # Set registry path
    if registry_file:
        registry_path = registry_file
    elif registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH
    
    app.logger.info(f"Using registry path: {registry_path}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Load or create registry
    if os.path.exists(registry_path):
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            app.logger.info(f"Loaded registry with {len(registry.get('goats', []))} goats")
        except Exception as e:
            app.logger.error(f"Error loading registry: {str(e)}")
            registry = {"goats": [], "default": None, "active": None}
    else:
        # Create default registry
        registry = {"goats": [], "default": None, "active": None}
        app.logger.info(f"Creating new registry at {registry_path}")
        save_registry()
    
    # Set active goat
    # First try the active field, then fall back to default
    active_goat_name_from_registry = registry.get("active") or registry.get("default")
    if active_goat_name_from_registry:
        set_active_goat(active_goat_name_from_registry)

def save_registry():
    """Save the registry to the registry file"""
    try:
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=4)
        return True
    except Exception as e:
        app.logger.error(f"Error saving registry: {str(e)}")
        return False

def set_active_goat(goat_name):
    """Set the active goat"""
    global active_goat, active_goat_name
    
    # Find the goat in the registry
    goat_config = None
    for goat in registry.get("goats", []):
        if goat.get("name") == goat_name:
            goat_config = goat
            break
    
    if not goat_config:
        return False
    
    # Initialize the appropriate goat type
    goat_type = goat_config.get("type")
    
    success = False
    try:
        if goat_type == "text":
            from mojogoat.goatbases.textgoat import TextGoat
            active_goat = TextGoat(goat_config)
            success = True
        elif goat_type == "neo4j":
            try:
                # Try to import from both neo4j goat implementations
                from mojogoat.goatbases.neo4jgoat import Neo4jGoat
                    
                active_goat = Neo4jGoat(goat_config.get("config_path"))
                success = True
            except ImportError:
                app.logger.error("Failed to import Neo4jGoat")
        elif goat_type == "mongopg":
            # Configure the app for MongoDB and PostgreSQL
            app.config['SQLALCHEMY_DATABASE_URI'] = goat_config.get("postgres_uri", "postgresql://postgres:postgres@localhost:5432/xetrapal")
            app.config['MONGODB_SETTINGS'] = {
                'host': goat_config.get("mongodb_uri", f"mongodb://localhost/{goat_name}")
            }
            
            # For testing purposes, use a special approach
            # This avoids 'AssertionError: The setup method ... can no longer be called'
            if app.config.get('TESTING', False):
                # For test environment, create a simple MongoDBPostgresGoat-like object
                from mojogoat.goatbases.mongogoat.models import MongoDBPostgresGoat
                active_goat = MongoDBPostgresGoat(goat_config)
                success = True
            else:
                # Initialize database connections for production
                try:
                    sqldb.init_app(app)
                    mongodb.init_app(app)
                    
                    # Create a MongoDB+PostgreSQL goat handler
                    from mojogoat.goatbases.mongogoat.models import MongoDBPostgresGoat
                    active_goat = MongoDBPostgresGoat(goat_config)
                    success = True
                except Exception as e:
                    app.logger.error(f"Failed to initialize database connections: {str(e)}")
        else:
            app.logger.error(f"Unsupported goat type: {goat_type}")
    except Exception as e:
        app.logger.error(f"Failed to set up goat: {str(e)}")
    
    if success:
        active_goat_name = goat_name
        
        # Update the active goat reference in routes
        try:
            from mojogoat.routes import set_active_goat_ref
            set_active_goat_ref(active_goat)
            app.logger.info(f"Set active goat reference for routes: {goat_name}")
        except Exception as e:
            app.logger.error(f"Failed to update routes with active goat: {str(e)}")
    
    return success

# API Routes

@app.route('/api/goats', methods=['GET'])
def list_goats():
    """List all goats in the registry"""
    return jsonify({
        "goats": registry.get("goats", []),
        "default": registry.get("default"),
        "active": active_goat_name,
        "registry_active": registry.get("active")
    })

@app.route('/api/goats', methods=['POST'])
def create_goat():
    """Create a new goat"""
    data = request.json
    
    if not data or not data.get("name") or not data.get("type"):
        return jsonify({"error": "Missing required fields: name and type"}), 400
    
    # Check if goat already exists
    for goat in registry.get("goats", []):
        if goat.get("name") == data.get("name"):
            return jsonify({"error": f"Goat with name '{data.get('name')}' already exists"}), 409
    
    # Create goat config
    goat_config = {
        "name": data.get("name"),
        "type": data.get("type"),
        "description": data.get("description", f"Goat created on {datetime.now().strftime('%Y-%m-%d')}"),
        "created": datetime.now().isoformat()
    }
    
    # Add type-specific configuration
    if data.get("type") == "text":
        if not data.get("goat_path"):
            return jsonify({"error": "Missing required field: goat_path for text goat"}), 400
        goat_config["goatpath"] = data.get("goat_path")
        goat_config["goatname"] = data.get("name")
        
    elif data.get("type") == "neo4j":
        if not data.get("config_path"):
            return jsonify({"error": "Missing required field: config_path for neo4j goat"}), 400
        goat_config["config_path"] = data.get("config_path")
        
    elif data.get("type") == "mongopg":
        goat_config["mongodb_uri"] = data.get("mongodb_uri", f"mongodb://localhost/{data.get('name')}")
        goat_config["postgres_uri"] = data.get("postgres_uri", "postgresql://postgres:postgres@localhost:5432/xetrapal")
        
        # Initialize databases if needed
        try:
            if data.get("create_db", False):
                # We would need to create the MongoDB database and PostgreSQL tables
                pass  # Implemented during initialization
        except Exception as e:
            return jsonify({"error": f"Failed to create databases: {str(e)}"}), 500
    else:
        return jsonify({"error": f"Unsupported goat type: {data.get('type')}"}), 400
    
    # Add to registry
    registry.setdefault("goats", []).append(goat_config)
    
    # Set as default if requested or if it's the first goat
    if data.get("make_default", False) or len(registry.get("goats", [])) == 1:
        registry["default"] = data.get("name")
    
    # Set as active if requested
    if data.get("make_active", False):
        registry["active"] = data.get("name")
    
    # Save registry
    if not save_registry():
        return jsonify({"error": "Failed to save registry"}), 500
    
    # Set as active goat in memory if requested
    if data.get("make_active", False):
        if not set_active_goat(data.get("name")):
            return jsonify({"error": "Failed to set as active goat"}), 500
    
    return jsonify({"message": f"Goat '{data.get('name')}' created successfully", "goat": goat_config}), 201

@app.route('/api/registry', methods=['GET'])
def get_registry_path():
    """Get the current registry path"""
    return jsonify({
        "registry_path": registry_path,
    })

@app.route('/api/registry', methods=['POST'])
def set_registry_path():
    """Set the registry path"""
    data = request.json
    
    if not data or not data.get("path"):
        return jsonify({"error": "Missing required field: path"}), 400
    
    global registry_path
    old_path = registry_path
    registry_path = data.get("path")
    
    # Try to load registry from new path
    if os.path.exists(registry_path):
        try:
            # Load new registry
            with open(registry_path, 'r') as f:
                new_registry = json.load(f)
            
            # Update registry (already declared as global)
            registry.clear()
            registry.update(new_registry)
            
            # Set active goat if default is specified
            if registry.get("default"):
                set_active_goat(registry["default"])
                
            return jsonify({"message": f"Registry path updated to {registry_path}"}), 200
        except Exception as e:
            registry_path = old_path  # Revert to old path on error
            return jsonify({"error": f"Failed to load registry from {data.get('path')}: {str(e)}"}), 500
    else:
        # Create new registry at specified path
        try:
            os.makedirs(os.path.dirname(registry_path), exist_ok=True)
            with open(registry_path, 'w') as f:
                json.dump({"goats": [], "default": None}, f, indent=4)
                
            # Create new registry (variables already declared as global)
            registry.clear()
            registry.update({"goats": [], "default": None})
            
            # Reset active goat
            global active_goat, active_goat_name
            active_goat = None
            active_goat_name = None
            
            return jsonify({"message": f"New registry created at {registry_path}"}), 201
        except Exception as e:
            registry_path = old_path  # Revert to old path on error
            return jsonify({"error": f"Failed to create registry at {data.get('path')}: {str(e)}"}), 500

@app.route('/api/active-goat', methods=['GET'])
def get_active_goat():
    """Get the currently active goat"""
    if not active_goat:
        return jsonify({"error": "No active goat selected"}), 404
    
    # Find the goat config
    goat_config = None
    for goat in registry.get("goats", []):
        if goat.get("name") == active_goat_name:
            goat_config = goat
            break
    
    return jsonify({
        "active_goat": active_goat_name,
        "config": goat_config,
        "is_default": registry.get("default") == active_goat_name,
        "is_registry_active": registry.get("active") == active_goat_name
    })

@app.route('/api/active-goat', methods=['POST'])
def set_active_goat_api():
    """Set the active goat"""
    data = request.json
    
    if not data or not data.get("name"):
        return jsonify({"error": "Missing required field: name"}), 400
    
    # Check if goat exists
    goat_exists = False
    for goat in registry.get("goats", []):
        if goat.get("name") == data.get("name"):
            goat_exists = True
            break
    
    if not goat_exists:
        return jsonify({"error": f"Goat with name '{data.get('name')}' does not exist"}), 404
    
    # Set active goat
    if not set_active_goat(data.get("name")):
        return jsonify({"error": f"Failed to set '{data.get('name')}' as active goat"}), 500
    
    # Update registry with active goat
    registry["active"] = data.get("name")
    
    # Update default if requested
    if data.get("make_default", False):
        registry["default"] = data.get("name")
    
    # Save registry
    save_registry()
    
    return jsonify({"message": f"Active goat set to '{data.get('name')}'"}), 200

# Add a direct endpoint for nodes to bypass the routes module
@app.route('/api/direct/nodes', methods=['GET'])
def direct_get_nodes():
    """Direct endpoint to get nodes bypassing the routes module"""
    if not active_goat:
        return jsonify({"error": "No active goat in direct route"}), 404
    
    try:
        nodes = active_goat.get_nodes()
        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get nodes: {str(e)}"}), 500

# Add a debug endpoint
@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Get debug information about the current state"""
    from mojogoat.routes import get_active_goat as routes_get_active_goat
    
    routes_active_goat = routes_get_active_goat()
    
    return jsonify({
        "api_active_goat": {
            "name": active_goat_name,
            "type": str(type(active_goat)) if active_goat else None,
            "is_none": active_goat is None
        },
        "routes_active_goat": {
            "type": str(type(routes_active_goat)) if routes_active_goat else None,
            "is_none": routes_active_goat is None,
            "is_same_instance": routes_active_goat is active_goat
        },
        "registry": {
            "path": registry_path,
            "default": registry.get("default"),
            "active": registry.get("active"),
            "goat_count": len(registry.get("goats", []))
        }
    }), 200

# Import and initialize routes for CRUD operations
from mojogoat.routes import init_routes, set_active_goat_ref

# Set the active goat reference for routes
set_active_goat_ref(active_goat)

# Initialize routes
init_routes(app)

# Initialize the app with command line arguments if provided
if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MojoGOAT API - Graph of All Things')
    parser.add_argument('--registry', '-r', 
                        help='Path to the registry file (default: $MOJOGOAT_REGISTRY or /xpal-data/conf/goat_registry.json)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                        help='Port to listen on (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set registry path if provided
    if args.registry:
        registry_path = args.registry
    
    # Initialize the app
    initialize_app()
    
    # Run the app
    app.run(debug=args.debug, host=args.host, port=args.port)
else:
    # Initialize the app for import cases (like tests)
    initialize_app()





    
