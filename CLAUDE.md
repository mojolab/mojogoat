# MojoGOAT Development Guidelines

## Execution Commands
- **Start services**: `./startmojogoat.sh`
- **Run API server**: `python mojogoatapi.py`
- **Run sync service**: `python mojogoatsync.py`
- **Database migration**: `alembic revision --autogenerate -m "message"` followed by `alembic upgrade head`

## Code Style Guidelines
- **Imports**: Group imports by standard library, third-party packages, and local modules
- **Naming**: Use snake_case for functions/variables, CamelCase for classes
- **Documentation**: Docstrings for classes and functions, inline comments for complex logic
- **Error Handling**: Use try/except with specific exceptions, log errors appropriately
- **Types**: Use type hints for function parameters and return values
- **Formatting**: 4-space indentation, 100 character line limit

## Database Patterns
- MongoDB for node storage using MongoEngine ODM
- PostgreSQL for relationship storage using SQLAlchemy ORM
- Neo4j for graph visualization and analysis

## API Format
- RESTful endpoints for CRUD operations on nodes and relationships
- Response format should be consistent JSON with proper error codes

---

## Modernisation Roadmap (for Xetrapal Phase 1 integration)

MojoGOAT is the quad engine dependency for Xetrapal's SmritiGraph. Before Phase 1 can proceed,
the following changes are required. Work in priority order:

1. **`pyproject.toml`** — already created. Run `uv sync` to verify.
2. **Async throughout** — all backend methods must be `async def`. Start with `textgoat.py`
   as the simplest backend, then `newneo4jgoat.py`, then mongogoat.
3. **UUID v4 IDs on write** — replace `rel_{index}` and auto-increment integers with
   `str(uuid4())` generated at write time.
4. **ISO-8601 timestamps** — standardise all timestamp fields to ISO-8601 strings.
5. **Arbitrary relationship properties on write** — `create_relationship()` must accept
   `**props` so callers (Xetrapal) can store fields like `state` without MojoGOAT caring.
6. **Retire `neo4jgoat.py`** — use `newneo4jgoat.py` (direct driver) as the only Neo4j
   backend. Remove py2neo dependency entirely.

### What NOT to change
- The Flask REST API layer can stay as-is for now — it's not used by Xetrapal directly.
- Do not touch the MongoDB+PostgreSQL backend until async migration of simpler backends is done.
- Do not change the quad model itself: `source | story | target | timestamp` is correct.

### Testing
Run existing tests after each change: `uv run pytest test/`
Add async test variants alongside the sync ones as you migrate.

### Xetrapal dependency setup
Xetrapal references MojoGOAT via:
```toml
# xetrapal3/pyproject.toml
[tool.uv.sources]
mojogoat = { path = "../mojogoat", editable = true }
```
Once stable, tag a release (`git tag v0.2.0`) and switch Xetrapal to a git tag reference.