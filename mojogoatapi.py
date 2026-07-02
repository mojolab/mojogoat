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

import asyncio
import io, os, re, sys
import json
import shutil
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

# Create Flask app
app = Flask(__name__)
CORS(app)

# Default registry location
DEFAULT_REGISTRY_PATH = os.environ.get('MOJOGOAT_REGISTRY', '/xpal-data/conf/goat_registry.json')

# Default data directory for the text backend fallback
DEFAULT_DATA_DIR = os.environ.get('MOJOGOAT_DATA', '/xpal-data/goats')

# Map class names to canonical backend type strings
_BACKEND_TYPE_MAP = {
    'FalkorGoat': 'falkordb',
    'TextGoat':   'text',
    'MemoryGoat': 'memory',
    'Neo4jGoat':  'neo4j',
}


def _get_backend_type(goat) -> str:
    return _BACKEND_TYPE_MAP.get(type(goat).__name__, 'unknown')


# ---------------------------------------------------------------------------
# Backend probing helpers
# ---------------------------------------------------------------------------

async def _probe_falkordb(config: dict):
    """Try to connect to FalkorDB. Returns a FalkorGoat on success, None on failure."""
    try:
        from mojogoat.goatbases.falkorgoat import FalkorGoat
        goat = FalkorGoat(
            host=config.get('host', 'localhost'),
            port=int(config.get('port', 6379)),
            graph_name=config.get('graph_name', 'mojogoat'),
            password=config.get('password'),
        )
        await asyncio.wait_for(goat.get_nodes(), timeout=2.0)
        return goat
    except Exception:
        return None


async def _probe_neo4j(config: dict):
    """Try to connect to Neo4j. Returns a Neo4jGoat on success, None on failure."""
    try:
        from mojogoat.goatbases.neo4jgoat import Neo4jGoat
        goat = Neo4jGoat(config['config_path'])
        await asyncio.wait_for(goat.get_nodes(), timeout=2.0)
        return goat
    except Exception:
        return None


def _make_textgoat(config: dict):
    """Instantiate a TextGoat, creating the data directory if needed."""
    from mojogoat.goatbases.textgoat import TextGoat
    goat_path = config.get('goat_path', os.path.join(DEFAULT_DATA_DIR, 'textgoat'))
    goat_name = config.get('goat_name', 'default')
    return TextGoat({'goatpath': goat_path, 'goatname': goat_name})


def _make_memorygoat():
    from mojogoat.goatbases.memorygoat import MemoryGoat
    return MemoryGoat()


async def _select_backend(requested_type: str, config: dict):
    """Instantiate and probe *requested_type*. Returns (goat, type_name).

    If *requested_type* is ``"auto"``, tries falkordb → text → memory in order.
    Raises ValueError for unsupported types or unavailable explicit backends.
    """
    if requested_type == 'falkordb':
        goat = await _probe_falkordb(config)
        if goat is None:
            raise ValueError('FalkorDB is not reachable')
        return goat, 'falkordb'

    if requested_type == 'neo4j':
        if not config.get('config_path'):
            raise ValueError('neo4j backend requires config_path')
        goat = await _probe_neo4j(config)
        if goat is None:
            raise ValueError('Neo4j is not reachable')
        return goat, 'neo4j'

    if requested_type == 'text':
        return _make_textgoat(config), 'text'

    if requested_type == 'memory':
        return _make_memorygoat(), 'memory'

    if requested_type == 'auto':
        # Auto mode uses only local backends — Neo4j and FalkorDB require
        # explicit configuration and are never probed automatically (ADR-0010).
        try:
            goat = _make_textgoat(config)
            return goat, 'text'
        except Exception:
            pass
        return _make_memorygoat(), 'memory'

    raise ValueError(f"Unknown backend type '{requested_type}'. "
                     "Valid options: auto, falkordb, neo4j, text, memory")


def _activate(goat, type_name: str) -> None:
    """Set *goat* as the process-wide active goat."""
    global active_goat, active_goat_name
    active_goat = goat
    active_goat_name = f'backend:{type_name}'

# Global variables for registry (need to be declared before they're used)
active_goat = None
active_goat_name = None
registry_path = None
registry = {}
_last_activation_error = None  # set by set_active_goat() on failure, for clearer HTTP error bodies

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
    global active_goat, active_goat_name, _last_activation_error

    _last_activation_error = None

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
        elif goat_type == "falkordb":
            from mojogoat.goatbases.falkorgoat import FalkorGoat
            active_goat = FalkorGoat(
                host=goat_config.get("host", "localhost"),
                port=int(goat_config.get("port", 6379)),
                graph_name=goat_config.get("graph_name", "mojogoat"),
                password=goat_config.get("password"),
            )
            success = True
        elif goat_type == "memory":
            from mojogoat.goatbases.memorygoat import MemoryGoat
            active_goat = MemoryGoat()
            success = True
        elif goat_type == "neo4j":
            try:
                from mojogoat.goatbases.neo4jgoat import Neo4jGoat
                active_goat = Neo4jGoat(goat_config.get("config_path"))
                success = True
            except ImportError:
                _last_activation_error = (
                    "neo4j driver not installed — install the 'neo4j' optional dependency group"
                )
                app.logger.error(_last_activation_error)
        else:
            _last_activation_error = f"Unsupported goat type: {goat_type}"
            app.logger.error(_last_activation_error)
    except Exception as e:
        _last_activation_error = f"Failed to set up goat: {str(e)}"
        app.logger.error(_last_activation_error)

    if success:
        active_goat_name = goat_name

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
    goat_type = data.get("type")
    if goat_type == "text":
        goat_name = data.get("name")
        # Auto-derive data directory as DEFAULT_DATA_DIR/{name} if not explicitly supplied
        goat_path = data.get("goat_path") or os.path.join(DEFAULT_DATA_DIR, goat_name)
        goat_config["goatpath"] = goat_path
        goat_config["goatname"] = goat_name

    elif goat_type == "falkordb":
        goat_config["host"] = data.get("host", "localhost")
        goat_config["port"] = int(data.get("port", 6379))
        goat_config["graph_name"] = data.get("graph_name") or data.get("name")
        if data.get("password"):
            goat_config["password"] = data.get("password")

    elif goat_type == "memory":
        pass  # No additional storage config required

    elif goat_type == "neo4j":
        if not data.get("config_path"):
            return jsonify({"error": "Missing required field: config_path for neo4j goat"}), 400
        goat_config["config_path"] = data.get("config_path")

    else:
        return jsonify({"error": f"Unsupported goat type: {data.get('type')}. "
                                  "Valid types: text, falkordb, memory, neo4j"}), 400
    
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
            if _last_activation_error:
                return jsonify({"error": _last_activation_error}), 400
            return jsonify({"error": "Failed to set as active goat"}), 500
    
    return jsonify({"message": f"Goat '{data.get('name')}' created successfully", "goat": goat_config}), 201


@app.route('/api/goats/<name>/summary', methods=['GET'])
async def goat_summary(name):
    """Return node count, rel count, and taxonomy for a named goat without changing the active goat."""
    goat_cfg = next((g for g in registry.get('goats', []) if g.get('name') == name), None)
    if goat_cfg is None:
        return jsonify({'error': f"Goat '{name}' not found"}), 404

    goat_type = goat_cfg.get('type')
    is_active = (name == active_goat_name)

    def _ok(node_count, rel_count, taxonomy):
        return jsonify({'name': name, 'type': goat_type, 'active': is_active,
                        'node_count': node_count, 'rel_count': rel_count, 'taxonomy': taxonomy})

    def _unavailable(note=None, error=None):
        d = {'name': name, 'type': goat_type, 'active': is_active,
             'node_count': None, 'rel_count': None, 'taxonomy': {}}
        if note:
            d['note'] = note
        if error:
            d['error'] = error
        return jsonify(d)

    try:
        if goat_type == 'text':
            from mojogoat.goatbases.textgoat import TextGoat
            g = TextGoat(goat_cfg)
            nodes, rels, taxonomy = await asyncio.gather(
                g.get_nodes(), g.get_relationships(), g.get_taxonomy()
            )
            return _ok(len(nodes), len(rels), taxonomy)

        if goat_type == 'memory':
            if is_active and active_goat is not None:
                nodes, rels, taxonomy = await asyncio.gather(
                    active_goat.get_nodes(), active_goat.get_relationships(), active_goat.get_taxonomy()
                )
                return _ok(len(nodes), len(rels), taxonomy)
            return _unavailable(note='in-memory state only accessible when active')

        if goat_type == 'falkordb':
            try:
                from mojogoat.goatbases.falkorgoat import FalkorGoat
                g = FalkorGoat(
                    host=goat_cfg.get('host', 'localhost'),
                    port=int(goat_cfg.get('port', 6379)),
                    graph_name=goat_cfg.get('graph_name', name),
                    password=goat_cfg.get('password'),
                )
                nodes, rels, taxonomy = await asyncio.wait_for(
                    asyncio.gather(g.get_nodes(), g.get_relationships(), g.get_taxonomy()),
                    timeout=2.0,
                )
                return _ok(len(nodes), len(rels), taxonomy)
            except Exception:
                return _unavailable(error='service unavailable')

        if goat_type == 'neo4j':
            try:
                from mojogoat.goatbases.neo4jgoat import Neo4jGoat
                g = Neo4jGoat(goat_cfg.get('config_path'))
                nodes, rels, taxonomy = await asyncio.wait_for(
                    asyncio.gather(g.get_nodes(), g.get_relationships(), g.get_taxonomy()),
                    timeout=3.0,
                )
                await g.close()
                return _ok(len(nodes), len(rels), taxonomy)
            except Exception:
                return _unavailable(error='service unavailable')

        return jsonify({'error': f"Unsupported type: {goat_type}"}), 400

    except Exception as e:
        return jsonify({'name': name, 'type': goat_type, 'error': str(e)}), 500


@app.route('/api/goats/<name>', methods=['DELETE'])
async def delete_goat(name):
    """Remove a goat from the registry.

    Query params:
        purge=true  — also destroy the backend storage (TextGoat: rm -rf data dir;
                      FalkorDB: drop the graph; Neo4j: DETACH DELETE all nodes).
                      Irreversible. MemoryGoat has nothing to purge.
    """
    global active_goat, active_goat_name

    goat_cfg = next((g for g in registry.get('goats', []) if g.get('name') == name), None)
    if goat_cfg is None:
        return jsonify({'error': f"Goat '{name}' not found"}), 404

    purge = request.args.get('purge', '').lower() == 'true'
    goat_type = goat_cfg.get('type')
    purge_error = None

    if purge:
        try:
            if goat_type == 'text':
                goat_path = goat_cfg.get('goatpath')
                if goat_path and os.path.isdir(goat_path):
                    shutil.rmtree(goat_path)

            elif goat_type == 'falkordb':
                from mojogoat.goatbases.falkorgoat import FalkorGoat
                g = FalkorGoat(
                    host=goat_cfg.get('host', 'localhost'),
                    port=int(goat_cfg.get('port', 6379)),
                    graph_name=goat_cfg.get('graph_name', name),
                    password=goat_cfg.get('password'),
                )
                await asyncio.wait_for(g._graph.delete(), timeout=5.0)
                await g.close()

            elif goat_type == 'neo4j':
                from mojogoat.goatbases.neo4jgoat import Neo4jGoat
                g = Neo4jGoat(goat_cfg.get('config_path'))
                async with g.driver.session() as session:
                    await asyncio.wait_for(
                        session.run("MATCH (n) DETACH DELETE n"),
                        timeout=10.0,
                    )
                await g.close()

            # memory: nothing to purge

        except Exception as exc:
            purge_error = str(exc)

    # Deactivate in memory if this was the active goat
    if name == active_goat_name:
        if active_goat is not None:
            try:
                await active_goat.close()
            except Exception:
                pass
        active_goat = None
        active_goat_name = None

    # Remove from registry
    registry['goats'] = [g for g in registry.get('goats', []) if g.get('name') != name]
    if registry.get('default') == name:
        registry['default'] = None
    if registry.get('active') == name:
        registry['active'] = None

    if not save_registry():
        return jsonify({'error': 'Failed to save registry after deletion'}), 500

    response = {'message': f"Goat '{name}' deleted", 'purged': purge}
    if purge_error:
        response['purge_warning'] = f"Registry entry removed but backend purge failed: {purge_error}"
    return jsonify(response), 200


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
        if _last_activation_error:
            return jsonify({"error": _last_activation_error}), 400
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

# ---------------------------------------------------------------------------
# Status / self-test
# ---------------------------------------------------------------------------

@app.route('/api/status', methods=['GET'])
def get_status():
    """API self-test — returns config, goat list, backend availability, and operation index."""
    import importlib.util

    def _can_import(module_name: str) -> bool:
        return importlib.util.find_spec(module_name) is not None

    backends = {
        "text":     {"available": True,                    "description": "File-based flat-file backend"},
        "memory":   {"available": True,                    "description": "In-memory backend (no persistence, resets on restart)"},
        "neo4j":    {"available": _can_import("neo4j"),    "description": "Neo4j graph database — recommended production backend (ADR-0010)"},
        "falkordb": {"available": _can_import("falkordb"), "description": "FalkorDB graph database — opt-in, Redis-native deployments only (ADR-0010)"},
    }

    active_info = None
    if active_goat:
        goat_cfg = next(
            (g for g in registry.get("goats", []) if g.get("name") == active_goat_name),
            None,
        )
        active_info = {
            "name": active_goat_name,
            "type": _get_backend_type(active_goat),
            "class": type(active_goat).__name__,
        }
        if goat_cfg:
            for key in ("goatpath", "host", "port", "graph_name"):
                if key in goat_cfg:
                    active_info[key] = goat_cfg[key]

    goats = [
        {
            "name": g.get("name"),
            "type": g.get("type"),
            "is_default": registry.get("default") == g.get("name"),
            "is_active": active_goat_name == g.get("name"),
            **{k: v for k, v in g.items() if k not in ("name", "type", "description", "created")},
        }
        for g in registry.get("goats", [])
    ]

    operations = [
        {"method": "GET",    "path": "/health",                             "description": "Liveness check — always 200 if the server is up"},
        {"method": "GET",    "path": "/api/status",                         "description": "API self-test (this endpoint)"},
        {"method": "GET",    "path": "/api/goats",                          "description": "List all registered goats"},
        {"method": "POST",   "path": "/api/goats",                          "description": "Create a new goat (type: text|falkordb|memory|neo4j)"},
        {"method": "GET",    "path": "/api/active-goat",                    "description": "Get the currently active goat"},
        {"method": "POST",   "path": "/api/active-goat",                    "description": "Switch the active goat by name"},
        {"method": "GET",    "path": "/api/backend",                        "description": "Get current backend type"},
        {"method": "POST",   "path": "/api/backend",                        "description": "Switch backend (type: auto|text|memory|falkordb|neo4j)"},
        {"method": "GET",    "path": "/api/nodes",                          "description": "List all nodes"},
        {"method": "POST",   "path": "/api/nodes",                          "description": "Create or update a node (body: {nodeid, ...props})"},
        {"method": "GET",    "path": "/api/nodes/<nodeid>",                 "description": "Get a node by ID"},
        {"method": "PUT",    "path": "/api/nodes/<nodeid>",                 "description": "Update a node"},
        {"method": "DELETE", "path": "/api/nodes/<nodeid>",                 "description": "Delete a node"},
        {"method": "GET",    "path": "/api/nodes/label/<label>",            "description": "List nodes by label"},
        {"method": "GET",    "path": "/api/relationships",                  "description": "List relationships (query params: source, target, story)"},
        {"method": "POST",   "path": "/api/relationships",                  "description": "Create a relationship (body: {source, target, story, ...props})"},
        {"method": "GET",    "path": "/api/relationships/<id>",             "description": "Get a relationship by ID"},
        {"method": "PATCH",  "path": "/api/relationships/<id>",             "description": "Update relationship properties (body: {...props})"},
        {"method": "DELETE", "path": "/api/relationships/<id>",             "description": "Delete a relationship"},
        {"method": "GET",    "path": "/api/active-goat/composition",        "description": "Node count grouped by label"},
        {"method": "GET",    "path": "/api/active-goat/taxonomy",           "description": "Relationship count grouped by story"},
        {"method": "POST",   "path": "/api/active-goat/dump-relationships", "description": "Dump all relationships to a file (body: {filename})"},
        {"method": "POST",   "path": "/api/active-goat/compact",            "description": "Compact TextGoat snapshots — rewrite current state, delete orphaned snapshots (ADR-0007)"},
        {"method": "POST",   "path": "/api/active-goat/import-relationships","description": "Bulk import from a pipe-delimited quad file (body: {filename}) — returns {imported, skipped, errors}"},
        {"method": "GET",    "path": "/api/graph",                          "description": "Graph data — {nodes, edges, node_count, edge_count}; filters: source, target, story, limit, node_ids (ADR-0011)"},
        {"method": "POST",   "path": "/api/operations",                     "description": "Create an operation (body: {name, node_ids, params}) (ADR-0012)"},
        {"method": "GET",    "path": "/api/operations/<id>",                "description": "Get operation status and results (ADR-0012)"},
        {"method": "POST",   "path": "/api/operations/<id>/results",        "description": "External process posts proposed changes (ADR-0012)"},
        {"method": "POST",   "path": "/api/operations/<id>/validate",       "description": "Accept or reject individual results (body: {result_id, action}) (ADR-0012)"},
        {"method": "DELETE", "path": "/api/operations/<id>",                "description": "Cancel and discard an operation (ADR-0012)"},
    ]

    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "registry_path": registry_path,
            "default_data_dir": DEFAULT_DATA_DIR,
        },
        "active_goat": active_info,
        "goats": goats,
        "backends": backends,
        "operations": operations,
    }), 200


# ---------------------------------------------------------------------------
# Health / liveness
# ---------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    """Liveness check — returns 200 if the server is running."""
    return jsonify({
        "status": "ok",
        "goat_count": len(registry.get("goats", [])),
        "active_goat": active_goat_name,
    }), 200


# ---------------------------------------------------------------------------
# Backend selection API
# ---------------------------------------------------------------------------

@app.route('/api/backend', methods=['GET'])
def get_backend():
    """Return the currently active backend type and class name."""
    if not active_goat:
        return jsonify({'type': None, 'class': None}), 200
    return jsonify({
        'type': _get_backend_type(active_goat),
        'class': type(active_goat).__name__,
    }), 200


@app.route('/api/backend', methods=['POST'])
async def set_backend():
    """Select the active backend store.

    Request body (all fields optional):
      type        — "auto" | "falkordb" | "neo4j" | "text" | "memory"  (default: "auto")
      host        — FalkorDB / Neo4j host             (default: localhost)
      port        — FalkorDB port                     (default: 6379)
      graph_name  — FalkorDB graph name               (default: mojogoat)
      password    — FalkorDB password
      config_path — Neo4j JSON config file path       (required for neo4j)
      goat_path   — Text backend data directory
      goat_name   — Text backend name                 (default: default)

    Auto mode tries text → memory. Neo4j and FalkorDB require explicit configuration (ADR-0010).
    """
    data = request.json or {}
    requested_type = data.get('type', 'auto')

    try:
        goat, actual_type = await _select_backend(requested_type, data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'Failed to initialise backend: {exc}'}), 500

    _activate(goat, actual_type)
    app.logger.info(f"Backend set to {actual_type} (requested: {requested_type})")

    return jsonify({
        'type': actual_type,
        'class': type(goat).__name__,
        'requested': requested_type,
    }), 200


# Import and initialize routes for CRUD operations
from mojogoat.routes import init_routes

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

    # Auto-detect backend if registry didn't provide one
    if active_goat is None:
        loop = asyncio.new_event_loop()
        try:
            goat, goat_type = loop.run_until_complete(_select_backend('auto', {}))
            _activate(goat, goat_type)
            print(f" * Auto-selected backend: {goat_type}")
        except Exception as exc:
            print(f" * Backend auto-detection failed: {exc}")
        finally:
            loop.close()

    # Run the app
    app.run(debug=args.debug, host=args.host, port=args.port)
else:
    # Initialize the app for import cases (like tests)
    initialize_app()





    
