from .textgoat import TextGoat
from .falkorgoat import FalkorGoat as FalkorGoat  # noqa: F401

try:
    from .newneo4jgoatcopilot import Neo4jGoat
except ImportError:
    Neo4jGoat = None  # type: ignore[assignment,misc]
