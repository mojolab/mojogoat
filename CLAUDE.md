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