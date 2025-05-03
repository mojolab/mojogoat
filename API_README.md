# MojoGOAT API

A RESTful API for the Graph of All Things (GOAT) system, supporting different storage backends and CRUD operations.

## Running the API

```bash
./run_mojogoat_api.sh [options]
```

Options:
- `--registry, -r PATH`: Path to the registry file (default: $MOJOGOAT_REGISTRY or /xpal-data/conf/goat_registry.json)
- `--port, -p PORT`: Port to listen on (default: 5000)
- `--host HOST`: Host to bind to (default: 0.0.0.0)
- `--debug, -d`: Enable debug mode
- `--help, -h`: Show this help message

Example:
```bash
./run_mojogoat_api.sh -r /path/to/registry.json -p 8080 -d
```

## API Endpoints

### Goat Management

#### List all goats
```
GET /api/goats
```

#### Create a new goat
```
POST /api/goats
```
Body:
```json
{
  "name": "my_goat",
  "type": "text|neo4j|mongopg",
  "description": "My goat description",
  "make_default": true,
  "make_active": true,
  
  // For text goat:
  "goat_path": "/path/to/goat",
  
  // For neo4j goat:
  "config_path": "/path/to/neo4j_config.json",
  
  // For mongopg goat:
  "mongodb_uri": "mongodb://localhost/my_goat",
  "postgres_uri": "postgresql://postgres:postgres@localhost:5432/xetrapal",
  "create_db": true
}
```

#### Get registry location
```
GET /api/registry
```

#### Set registry location
```
POST /api/registry
```
Body:
```json
{
  "path": "/path/to/registry.json"
}
```

#### Get active goat
```
GET /api/active-goat
```

#### Set active goat
```
POST /api/active-goat
```
Body:
```json
{
  "name": "my_goat",
  "make_default": true
}
```

### Node Operations

#### Get all nodes
```
GET /api/nodes
```

#### Get a node by ID
```
GET /api/nodes/{nodeid}
```

#### Get nodes by label
```
GET /api/nodes/label/{label}
```

#### Create a node
```
POST /api/nodes
```
Body:
```json
{
  "nodeid": "my_node_id",
  "nodename": "My Node",
  "labels": ["Label1", "Label2"],
  "property1": "value1",
  "property2": "value2"
}
```

#### Update a node
```
PUT /api/nodes/{nodeid}
```
Body:
```json
{
  "nodename": "Updated Node",
  "property1": "new_value"
}
```

#### Delete a node
```
DELETE /api/nodes/{nodeid}
```

### Relationship Operations

#### Get all relationships
```
GET /api/relationships
```

Optional query parameters: `source`, `target`, `story`

#### Get a relationship by ID
```
GET /api/relationships/{relationship_id}
```

#### Create a relationship
```
POST /api/relationships
```
Body:
```json
{
  "source": "source_node_id",
  "target": "target_node_id",
  "story": "RELATES_TO"
}
```

#### Delete a relationship
```
DELETE /api/relationships/{relationship_id}
```

### Goat-specific Operations

#### Get node composition by label
```
GET /api/active-goat/composition
```

#### Get relationship taxonomy
```
GET /api/active-goat/taxonomy
```

#### Dump relationships to a file
```
POST /api/active-goat/dump-relationships
```
Body:
```json
{
  "filename": "/path/to/output.txt"
}
```

## Testing

To run the API tests:
```bash
python3 test/run_api_tests.py
```