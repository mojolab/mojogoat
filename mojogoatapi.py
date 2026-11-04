'''
MojoGOAT API - A Graph of All Things API

API v2 (ADR-016): there is no "active goat". Every goat-level route is
/api/goats/<goat>/... and the goat is resolved per request from the registry.
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
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

from mojogoat.errors import GoatNotFound, GoatUnavailable
from mojogoat.routes import init_routes, API_VERSION

# Create Flask app
app = Flask(__name__)
CORS(app)

# Default registry location
DEFAULT_REGISTRY_PATH = os.environ.get('MOJOGOAT_REGISTRY', '/xpal-data/conf/goat_registry.json')

# Default data directory for text goats created without an explicit goat_path
DEFAULT_DATA_DIR = os.environ.get('MOJOGOAT_DATA', '/xpal-data/goats')

# Goat names are URL path segments and (by default) directory names (ADR-016 section 8)
GOAT_NAME_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'
GOAT_NAME_RE = re.compile(GOAT_NAME_PATTERN)

# Globals for the registry
registry_path = None
registry = {}

# Goat instances opened so far, by name. Built lazily from the registry; this is resource
# state, not a "current goat" — nothing here is selected per client or per server.
_goat_cache: dict = {}
_goat_cache_lock = threading.Lock()


def _valid_goat_name(name) -> bool:
    # fullmatch, not match: '$' also matches before a trailing newline ("x\n")
    return isinstance(name, str) and GOAT_NAME_RE.fullmatch(name) is not None


def _registry_entry(name):
    return next((g for g in registry.get('goats', []) if g.get('name') == name), None)


# ---------------------------------------------------------------------------
# Goat construction and resolution
# ---------------------------------------------------------------------------

def _build_goat(goat_config: dict):
    """Instantiate the goat described by a registry entry. Raises GoatUnavailable."""
    goat_type = goat_config.get("type")
    try:
        if goat_type == "text":
            from mojogoat.goatbases.textgoat import TextGoat
            return TextGoat(goat_config)
        if goat_type == "falkordb":
            from mojogoat.goatbases.falkorgoat import FalkorGoat
            return FalkorGoat(
                host=goat_config.get("host", "localhost"),
                port=int(goat_config.get("port", 6379)),
                graph_name=goat_config.get("graph_name", "mojogoat"),
                password=goat_config.get("password"),
            )
        if goat_type == "memory":
            from mojogoat.goatbases.memorygoat import MemoryGoat
            return MemoryGoat()
        if goat_type == "neo4j":
            try:
                from mojogoat.goatbases.neo4jgoat import Neo4jGoat
            except ImportError:
                raise GoatUnavailable(
                    "neo4j driver not installed — install the 'neo4j' optional dependency group")
            return Neo4jGoat(goat_config.get("config_path"))
    except GoatUnavailable:
        raise
    except Exception as e:
        raise GoatUnavailable(f"Failed to set up goat: {str(e)}")
    raise GoatUnavailable(f"Unsupported goat type: {goat_type}")


def resolve_goat(name):
    """Return the GoatBase for registry goat *name* (cached).

    Raises GoatNotFound for an invalid or unknown name, GoatUnavailable if the goat is
    registered but cannot be opened.
    """
    if not _valid_goat_name(name):
        raise GoatNotFound(name)
    with _goat_cache_lock:
        goat = _goat_cache.get(name)
        if goat is not None:
            return goat
        entry = _registry_entry(name)
        if entry is None:
            raise GoatNotFound(name)
        goat = _build_goat(entry)
        _goat_cache[name] = goat
        return goat


async def _close_goat(goat) -> None:
    try:
        await goat.close()
    except Exception:
        pass


def _clear_goat_cache() -> list:
    with _goat_cache_lock:
        goats = list(_goat_cache.values())
        _goat_cache.clear()
    return goats


def initialize_app(registry_file=None):
    """Initialize the application with the registry file"""
    global registry, registry_path

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
            registry = {"goats": []}
    else:
        registry = {"goats": []}
        app.logger.info(f"Creating new registry at {registry_path}")
        save_registry()

    # ADR-016: there is no active or default goat. Old registries may still carry the fields;
    # ignore them (they are dropped on the next save).
    registry.pop("active", None)
    registry.pop("default", None)
    _clear_goat_cache()

    bad = [g.get("name") for g in registry.get("goats", []) if not _valid_goat_name(g.get("name"))]
    if bad:
        app.logger.warning(
            "Registry goat name(s) %s do not match %s and are unreachable through the scoped "
            "routes (ADR-016 section 8)", bad, GOAT_NAME_PATTERN)


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


# ---------------------------------------------------------------------------
# Goat management routes
# ---------------------------------------------------------------------------

@app.route('/api/goats', methods=['GET'])
def list_goats():
    """List all goats in the registry"""
    return jsonify({"goats": registry.get("goats", [])})


@app.route('/api/goats/<name>', methods=['GET'])
def get_goat(name):
    """Return one goat's registry entry (name, type, goatpath for text goats, ...)."""
    entry = _registry_entry(name) if _valid_goat_name(name) else None
    if entry is None:
        return jsonify({"error": f"Goat '{name}' not found"}), 404
    return jsonify(entry), 200


@app.route('/api/goats', methods=['POST'])
def create_goat():
    """Create a new goat"""
    data = request.json

    if not data or not data.get("name") or not data.get("type"):
        return jsonify({"error": "Missing required fields: name and type"}), 400

    if "make_active" in data or "make_default" in data:
        return jsonify({"error": "make_active/make_default were removed in API v2 (ADR-016); "
                                 "there is no active or default goat"}), 400

    goat_name = data.get("name")
    if not _valid_goat_name(goat_name):
        return jsonify({"error": f"Invalid goat name {goat_name!r}: must match {GOAT_NAME_PATTERN}"}), 400

    # Check if goat already exists
    if _registry_entry(goat_name) is not None:
        return jsonify({"error": f"Goat with name '{goat_name}' already exists"}), 409

    # Create goat config
    goat_config = {
        "name": goat_name,
        "type": data.get("type"),
        "description": data.get("description", f"Goat created on {datetime.now().strftime('%Y-%m-%d')}"),
        "created": datetime.now().isoformat()
    }

    # Add type-specific configuration
    goat_type = data.get("type")
    if goat_type == "text":
        explicit_path = data.get("goat_path")
        if explicit_path:
            # Caller's choice (admin); not confined to DEFAULT_DATA_DIR, but must be absolute.
            if not isinstance(explicit_path, str) or not os.path.isabs(explicit_path):
                return jsonify({"error": "goat_path must be an absolute path"}), 400
            goat_path = explicit_path
        else:
            goat_path = os.path.join(DEFAULT_DATA_DIR, goat_name)
            base = os.path.realpath(DEFAULT_DATA_DIR)
            try:
                inside = os.path.commonpath([os.path.realpath(goat_path), base]) == base
            except ValueError:
                inside = False
            if not inside:
                return jsonify({"error": "Derived goat path escapes the data directory"}), 400
        for other in registry.get("goats", []):
            if other.get("type") == "text" and other.get("goatpath") == goat_path:
                return jsonify({"error": f"goat_path '{goat_path}' is already used by "
                                         f"goat '{other.get('name')}'"}), 409
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

    # Text goats touch the filesystem on construction: open it now so an unwritable path is
    # reported here rather than on first use. Other types are built lazily.
    built = None
    if goat_type == "text":
        try:
            built = _build_goat(goat_config)
        except GoatUnavailable as e:
            return jsonify({"error": str(e)}), 400

    # Add to registry
    registry.setdefault("goats", []).append(goat_config)

    # Save registry
    if not save_registry():
        registry["goats"].remove(goat_config)
        return jsonify({"error": "Failed to save registry"}), 500

    if built is not None:
        with _goat_cache_lock:
            _goat_cache[goat_name] = built

    return jsonify({"message": f"Goat '{goat_name}' created successfully", "goat": goat_config}), 201


@app.route('/api/goats/<name>/summary', methods=['GET'])
async def goat_summary(name):
    """Return node count, rel count, and taxonomy for a named goat."""
    goat_cfg = _registry_entry(name)
    if goat_cfg is None:
        return jsonify({'error': f"Goat '{name}' not found"}), 404

    goat_type = goat_cfg.get('type')

    def _ok(node_count, rel_count, taxonomy):
        return jsonify({'name': name, 'type': goat_type,
                        'node_count': node_count, 'rel_count': rel_count, 'taxonomy': taxonomy})

    def _unavailable(note=None, error=None):
        d = {'name': name, 'type': goat_type,
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
            try:
                g = resolve_goat(name)
            except (GoatNotFound, GoatUnavailable) as e:
                return _unavailable(error=str(e))
            nodes, rels, taxonomy = await asyncio.gather(
                g.get_nodes(), g.get_relationships(), g.get_taxonomy()
            )
            return _ok(len(nodes), len(rels), taxonomy)

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
    goat_cfg = _registry_entry(name)
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

    # Drop (and close) any cached instance of this goat
    with _goat_cache_lock:
        cached = _goat_cache.pop(name, None)
    if cached is not None:
        await _close_goat(cached)

    # Remove from registry
    registry['goats'] = [g for g in registry.get('goats', []) if g.get('name') != name]

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
            registry.pop("active", None)
            registry.pop("default", None)
            _clear_goat_cache()

            return jsonify({"message": f"Registry path updated to {registry_path}"}), 200
        except Exception as e:
            registry_path = old_path  # Revert to old path on error
            return jsonify({"error": f"Failed to load registry from {data.get('path')}: {str(e)}"}), 500
    else:
        # Create new registry at specified path
        try:
            os.makedirs(os.path.dirname(registry_path), exist_ok=True)
            with open(registry_path, 'w') as f:
                json.dump({"goats": []}, f, indent=4)

            registry.clear()
            registry.update({"goats": []})
            _clear_goat_cache()

            return jsonify({"message": f"New registry created at {registry_path}"}), 201
        except Exception as e:
            registry_path = old_path  # Revert to old path on error
            return jsonify({"error": f"Failed to create registry at {data.get('path')}: {str(e)}"}), 500


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
        "neo4j":    {"available": _can_import("neo4j"),    "description": "Neo4j graph database — recommended production backend (ADR-010)"},
        "falkordb": {"available": _can_import("falkordb"), "description": "FalkorDB graph database — opt-in, Redis-native deployments only (ADR-010)"},
    }

    goats = [
        {
            "name": g.get("name"),
            "type": g.get("type"),
            **{k: v for k, v in g.items() if k not in ("name", "type", "description", "created")},
        }
        for g in registry.get("goats", [])
    ]

    operations = [
        {"method": "GET",    "path": "/health",                                          "description": "Liveness check — always 200 if the server is up"},
        {"method": "GET",    "path": "/api/status",                                      "description": "API self-test (this endpoint)"},
        {"method": "GET",    "path": "/api/goats",                                       "description": "List all registered goats"},
        {"method": "POST",   "path": "/api/goats",                                       "description": "Create a new goat (type: text|falkordb|memory|neo4j)"},
        {"method": "GET",    "path": "/api/goats/<goat>",                                "description": "Get one goat's registry entry"},
        {"method": "DELETE", "path": "/api/goats/<goat>",                                "description": "Remove a goat (purge=true also destroys its storage)"},
        {"method": "GET",    "path": "/api/goats/<goat>/summary",                        "description": "Node/relationship counts and taxonomy for a goat"},
        {"method": "GET",    "path": "/api/goats/<goat>/nodes",                          "description": "List all nodes"},
        {"method": "POST",   "path": "/api/goats/<goat>/nodes",                          "description": "Create or update a node (body: {nodeid, ...props})"},
        {"method": "GET",    "path": "/api/goats/<goat>/nodes/<nodeid>",                 "description": "Get a node by ID"},
        {"method": "PUT",    "path": "/api/goats/<goat>/nodes/<nodeid>",                 "description": "Update a node"},
        {"method": "DELETE", "path": "/api/goats/<goat>/nodes/<nodeid>",                 "description": "Delete a node"},
        {"method": "GET",    "path": "/api/goats/<goat>/nodes/label/<label>",            "description": "List nodes by label"},
        {"method": "GET",    "path": "/api/goats/<goat>/relationships",                  "description": "List relationships (query params: source, target, story)"},
        {"method": "POST",   "path": "/api/goats/<goat>/relationships",                  "description": "Create a relationship (body: {source, target, story, ...props})"},
        {"method": "GET",    "path": "/api/goats/<goat>/relationships/<id>",             "description": "Get a relationship by ID"},
        {"method": "PATCH",  "path": "/api/goats/<goat>/relationships/<id>",             "description": "Update relationship properties (body: {...props})"},
        {"method": "DELETE", "path": "/api/goats/<goat>/relationships/<id>",             "description": "Delete a relationship"},
        {"method": "GET",    "path": "/api/goats/<goat>/composition",                    "description": "Node count grouped by label"},
        {"method": "GET",    "path": "/api/goats/<goat>/taxonomy",                       "description": "Relationship count grouped by story"},
        {"method": "POST",   "path": "/api/goats/<goat>/dump-relationships",             "description": "Dump all relationships to a file (body: {filename})"},
        {"method": "POST",   "path": "/api/goats/<goat>/compact",                        "description": "Compact TextGoat snapshots — rewrite current state, delete orphaned snapshots (ADR-007)"},
        {"method": "POST",   "path": "/api/goats/<goat>/import-relationships",           "description": "Bulk import from a pipe-delimited quad file (body: {filename}) — returns {imported, skipped, errors}"},
        {"method": "GET",    "path": "/api/goats/<goat>/graph",                          "description": "Graph data — {nodes, edges, node_count, edge_count}; filters: source, target, story, limit, node_ids (ADR-011)"},
        {"method": "GET",    "path": "/api/goats/<goat>/operations",                     "description": "List this goat's operations (ADR-012, ADR-016)"},
        {"method": "POST",   "path": "/api/goats/<goat>/operations",                     "description": "Create an operation (body: {name, node_ids, params}) (ADR-012)"},
        {"method": "GET",    "path": "/api/goats/<goat>/operations/<id>",                "description": "Get operation status and results (ADR-012)"},
        {"method": "POST",   "path": "/api/goats/<goat>/operations/<id>/results",        "description": "External process posts proposed changes (ADR-012)"},
        {"method": "POST",   "path": "/api/goats/<goat>/operations/<id>/validate",       "description": "Accept or reject individual results (body: {result_id, action}) (ADR-012)"},
        {"method": "DELETE", "path": "/api/goats/<goat>/operations/<id>",                "description": "Cancel and discard an operation (ADR-012)"},
    ]

    return jsonify({
        "status": "ok",
        "api_version": API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "registry_path": registry_path,
            "default_data_dir": DEFAULT_DATA_DIR,
        },
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
    }), 200


# Goat-scoped routes (ADR-016) and 410 stubs for the removed v1 routes
init_routes(app, resolve_goat)

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

    # Reload any operations left awaiting validation across a restart (ADR-014)
    from mojogoat import operations
    loaded = operations.load_persisted()
    if loaded:
        print(f" * Reloaded {loaded} persisted operation(s)")

    # Run the app
    app.run(debug=args.debug, host=args.host, port=args.port)
else:
    # Initialize the app for import cases (like tests)
    initialize_app()
