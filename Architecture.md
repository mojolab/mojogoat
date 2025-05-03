# MojoGOAT Architecture

## The Quad Structure

MojoGOAT organizes information using a semantic structure called a "quad" that consists of four parts:

1. **Source Node (Subject)**: The entity that initiates the relationship
2. **Story (Predicate)**: The nature of the relationship between entities
3. **Target Node (Object)**: The entity that receives the relationship
4. **Timestamp (Context)**: When the relationship was established or recorded

Example of a quad:
```
PersonA|knows|PersonB|2025-01-05
```

This structure extends the traditional semantic triple (subject-predicate-object) by adding a temporal component, allowing for time-based queries and historical analysis of relationships.

Quads are stored in various formats depending on the storage backend:
- As pipe-delimited text in text files
- As graph relationships in Neo4j
- As relationship records in PostgreSQL with references to MongoDB documents

## Storage Backends

MojoGOAT implements multiple storage backends ("goatbases") that can be used interchangeably:

### 1. Neo4j Graph Database

**Implementation**: `neo4jgoat.py` and `newneo4jgoat.py`

- Uses py2neo to interact with Neo4j
- Represents quads as graph relationships between nodes
- Provides native graph traversal and visualization capabilities
- Supports graph algorithms for advanced analysis
- Nodes have labels and properties corresponding to their attributes
- Relationships have types (the "story") and properties (including timestamp)

**Strengths**:
- Native graph structure and optimized for relationship queries
- Powerful visualization and traversal capabilities
- Supports complex graph algorithms

### 2. Text-based Storage

**Implementation**: `textgoat.py`

- Stores nodes as JSON files in a directory structure
- Stores relationships as pipe-delimited text in plain files
- Uses simple file operations for data management
- Supports Git-based versioning for data changes
- Organizes data in `nodes` and `snapshots` directories

**Strengths**:
- Simple, portable storage without database dependencies
- Human-readable format
- Natural Git integration for versioning
- Easy backup and migration

### 3. MongoDB + PostgreSQL Hybrid

**Implementation**: `mongogoat/models.py` and related controllers

- **MongoDB**: Stores node documents with flexible schemas
  - Uses mongoengine for ODM (Object Document Mapping)
  - Supports dynamic properties on nodes
  - Handles specialized node types like Person, Contact, etc.
  
- **PostgreSQL**: Stores relationship records as structured data
  - Uses SQLAlchemy for ORM (Object Relational Mapping)
  - Represents quads as records with source_id, target_id, story, and timestamp
  - Provides strong consistency for relationship data

**Strengths**:
- MongoDB's flexibility for varied node attributes
- PostgreSQL's reliability for relationship integrity
- SQL capabilities for complex relationship queries
- MongoDB's document model for rich node data

## CRUD Operations

MojoGOAT provides standardized CRUD operations across all storage backends:

- **Create**: Add new nodes and relationships
- **Read**: Query nodes by ID or properties, search relationships
- **Update**: Modify node properties or relationship attributes
- **Delete**: Remove nodes or relationships

Each implementation provides consistent methods despite different underlying storage technologies.

## Synchronization

The `mojogoatsync.py` service ensures data consistency across different storage backends by:
1. Detecting differences between node sets in different stores
2. Copying missing nodes and relationships as needed
3. Updating node labels and properties to ensure consistency
4. Running periodically to keep all systems in sync

This architecture allows MojoGOAT to leverage the strengths of different storage systems while maintaining a consistent data model and interface.