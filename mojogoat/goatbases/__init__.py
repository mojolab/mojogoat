from .textgoat import TextGoat

try:
    from .newneo4jgoatcopilot import Neo4jGoat
except ImportError:
    Neo4jGoat = None  # type: ignore[assignment,misc]
