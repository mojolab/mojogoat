from .base import GoatBase, REL_CONNECTED, REL_IDENTITY
from .textgoat import TextGoat
from .falkorgoat import FalkorGoat as FalkorGoat  # noqa: F401

try:
    from .neo4jgoat import Neo4jGoat
except ImportError:
    Neo4jGoat = None  # type: ignore[assignment,misc]
