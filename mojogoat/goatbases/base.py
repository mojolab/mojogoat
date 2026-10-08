import json
from abc import ABC, abstractmethod

# Cypher relationship type constants — shared by all graph backends.
REL_CONNECTED = "is_connected_to"
REL_IDENTITY = "is_the_same_as"

# Quad fields returned by get_relationships()/get_relationship() — everything
# else in the dict is caller-supplied props.
_QUAD_FIELDS = {"source_id", "story", "target_id", "timestamp", "relationship_id"}


def format_dump_line(rel: dict) -> str:
    """Serialize a relationship dict to the pipe-delimited dump-file format.

    Includes relationship_id and props so dump_all_rels() is a faithful
    inverse of import-relationships — a round trip must not lose data.
    """
    line = (
        f"{rel['source_id']}|{rel['story']}|{rel['target_id']}|"
        f"{rel['timestamp']}|{rel['relationship_id']}"
    )
    props = {k: v for k, v in rel.items() if k not in _QUAD_FIELDS}
    if props:
        line += f"|{json.dumps(props, separators=(',', ':'))}"
    return line


class GoatBase(ABC):
    """Abstract base class defining the MojoGOAT backend interface.

    Every backend (TextGoat, FalkorGoat, Neo4jGoat, …) must implement all
    methods declared here.  Callers should type-hint against ``GoatBase`` so
    that backends are drop-in replaceable.
    """

    @abstractmethod
    async def add_node(self, nodeid: str, **kwargs) -> dict: ...

    @abstractmethod
    async def get_node(self, nodeid: str) -> dict | None: ...

    @abstractmethod
    async def get_nodes(self) -> list[dict]: ...

    @abstractmethod
    async def get_nodes_by_label(self, label: str) -> list[dict]: ...

    @abstractmethod
    async def delete_node(self, nodeid: str) -> bool: ...

    @abstractmethod
    async def get_relationships(
        self,
        source: str | None = None,
        target: str | None = None,
        story: str | None = None,
        props: dict | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]: ...

    @abstractmethod
    async def get_relationship(self, relationship_id: str) -> dict | None: ...

    @abstractmethod
    async def create_relationship(
        self, source: str, target: str, story: str, **props
    ) -> dict | None: ...

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Remove a relationship permanently. Returns True if found.

        WARNING: Do not call this in normal application flow. Use update_relationship_props()
        to mark relationships as invalid via **props (e.g. state='invalidated'). This method
        exists for administrative correction and test teardown only. See ADR-008.
        """
        ...

    @abstractmethod
    async def update_relationship_props(
        self, relationship_id: str, **props
    ) -> bool: ...

    @abstractmethod
    async def get_composition(self) -> dict[str, int]: ...

    @abstractmethod
    async def get_taxonomy(self) -> dict[str, int]: ...

    @abstractmethod
    async def dump_all_rels(self, path: str) -> int: ...

    @abstractmethod
    async def link_is(self, node1_id: str, node2_id: str) -> None: ...

    async def close(self) -> None:
        """Close any underlying connections. No-op for backends with no connection."""
        pass
