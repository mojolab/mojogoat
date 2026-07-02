from datetime import datetime
from uuid import uuid4

try:
    from falkordb.asyncio import FalkorDB as AsyncFalkorDB
except ImportError:
    AsyncFalkorDB = None  # type: ignore[assignment,misc]

from .base import GoatBase, REL_CONNECTED, REL_IDENTITY, format_dump_line


class FalkorGoat(GoatBase):
    """Async FalkorDB backend (Redis-based graph, Cypher query language).

    Relationship model
    ------------------
    Two Cypher relationship types:
      - ``is_connected_to`` — used for all domain relationships.
        The ``story`` value is stored in a ``stories`` list property so that
        queries can use ``WHERE $story IN r.stories``.
      - ``is_the_same_as`` — used for identity / equivalence pairs only
        (created via :meth:`link_is`).

    Constructor
    -----------
    ``FalkorGoat(host, port, graph_name, password=None)`` — all arguments are
    explicit so that no credentials are ever hard-coded in source.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        graph_name: str = "mojogoat",
        password: str | None = None,
    ) -> None:
        if AsyncFalkorDB is None:
            raise ImportError(
                "falkordb package is not installed. "
                "Run: pip install 'mojogoat[falkordb]'"
            )
        db = AsyncFalkorDB(host=host, port=port, password=password)
        self._graph = db.select_graph(graph_name)

    @classmethod
    def from_graph(cls, graph) -> "FalkorGoat":
        """Inject a pre-configured graph object — used in unit tests."""
        obj = cls.__new__(cls)
        obj._graph = graph
        return obj

    async def close(self) -> None:
        """Close the underlying FalkorDB connection (no-op if already closed)."""
        try:
            await self._graph.connection.aclose()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_to_dict(node) -> dict:
        """Convert a FalkorDB Node object to a plain dict."""
        data = dict(node.properties) if node.properties else {}
        # Prefer stored 'labels' property; fall back to structural labels.
        if "labels" not in data and node.labels:
            data["labels"] = list(node.labels)
        return data

    @staticmethod
    def _rel_to_quad(src_nodeid: str, rel, tgt_nodeid: str) -> dict:
        """Convert a FalkorDB Edge object into a quad-model dict."""
        props = dict(rel.properties) if rel.properties else {}
        stories: list = props.pop("stories", [])
        ts: str = props.pop("timestamp", "")
        rid: str = props.pop("relationship_id", "")
        return {
            "source_id": src_nodeid,
            "story": stories[0] if stories else "",
            "target_id": tgt_nodeid,
            "timestamp": ts,
            "relationship_id": rid,
            **props,
        }

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    async def add_node(self, nodeid: str, **kwargs) -> dict:
        """Create or update a node. Returns the node as a dict."""
        kwargs["nodeid"] = nodeid
        kwargs.setdefault("created", datetime.now().isoformat())
        kwargs["updated"] = datetime.now().isoformat()

        # Normalise labels to a list so they survive round-trips.
        if "labels" in kwargs and not isinstance(kwargs["labels"], list):
            kwargs["labels"] = [str(kwargs["labels"])]

        await self._graph.query(
            "MERGE (n:Node {nodeid: $nodeid}) SET n += $props",
            {"nodeid": nodeid, "props": kwargs},
        )
        return kwargs

    async def get_node(self, nodeid: str) -> dict | None:
        """Return a node dict by ID, or None."""
        result = await self._graph.query(
            "MATCH (n:Node {nodeid: $nodeid}) RETURN n",
            {"nodeid": nodeid},
        )
        if not result.result_set:
            return None
        return self._node_to_dict(result.result_set[0][0])

    async def get_nodes(self) -> list[dict]:
        """Return all nodes."""
        result = await self._graph.query("MATCH (n:Node) RETURN n")
        return [self._node_to_dict(row[0]) for row in result.result_set]

    async def get_nodes_by_label(self, label: str) -> list[dict]:
        """Return all nodes whose ``labels`` property contains *label*."""
        result = await self._graph.query(
            "MATCH (n:Node) WHERE $label IN n.labels RETURN n",
            {"label": label},
        )
        return [self._node_to_dict(row[0]) for row in result.result_set]

    async def delete_node(self, nodeid: str) -> bool:
        """Detach-delete a node. Returns True if it existed."""
        result = await self._graph.query(
            "MATCH (n:Node {nodeid: $nodeid}) "
            "DETACH DELETE n "
            "RETURN count(n) AS cnt",
            {"nodeid": nodeid},
        )
        if not result.result_set:
            return False
        return bool(result.result_set[0][0])

    # ------------------------------------------------------------------
    # Relationship CRUD
    # ------------------------------------------------------------------

    async def get_relationships(
        self,
        source: str | None = None,
        target: str | None = None,
        story: str | None = None,
        props: dict | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """Return ``is_connected_to`` relationships, optionally filtered."""
        conditions: list[str] = []
        params: dict = {}

        if source:
            conditions.append("n.nodeid = $source")
            params["source"] = source
        if target:
            conditions.append("m.nodeid = $target")
            params["target"] = target
        if story:
            conditions.append("$story IN r.stories")
            params["story"] = story
        if props:
            for k, v in props.items():
                param_name = f"prop_{k}"
                conditions.append(f"r.{k} = ${param_name}")
                params[param_name] = v

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        skip_clause = f" SKIP {int(offset)}" if offset is not None else ""
        limit_clause = f" LIMIT {int(limit)}" if limit is not None else ""
        query = (
            f"MATCH (n:Node)-[r:{REL_CONNECTED}]->(m:Node){where} "
            f"RETURN n.nodeid, r, m.nodeid{skip_clause}{limit_clause}"
        )
        result = await self._graph.query(query, params)
        return [
            self._rel_to_quad(row[0], row[1], row[2])
            for row in result.result_set
        ]

    async def get_relationship(self, relationship_id: str) -> dict | None:
        """Return a single relationship by UUID, or None if not found."""
        result = await self._graph.query(
            f"MATCH (n:Node)-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->(m:Node) "
            "RETURN n.nodeid, r, m.nodeid",
            {"rid": relationship_id},
        )
        if not result.result_set:
            return None
        row = result.result_set[0]
        return self._rel_to_quad(row[0], row[1], row[2])

    async def create_relationship(
        self,
        source: str,
        target: str,
        story: str,
        **props,
    ) -> dict | None:
        """Create an ``is_connected_to`` relationship.

        *story* is stored in a ``stories`` list property so the Cypher model
        can query it with ``WHERE $story IN r.stories``.  Any extra keyword
        arguments are stored verbatim on the edge.
        """
        rel_id = str(uuid4())
        ts = datetime.now().isoformat()
        rel_props: dict = {
            "stories": [story],
            "timestamp": ts,
            "relationship_id": rel_id,
            **props,
        }
        result = await self._graph.query(
            f"MATCH (n:Node {{nodeid: $src}}), (m:Node {{nodeid: $tgt}}) "
            f"CREATE (n)-[r:{REL_CONNECTED}]->(m) SET r += $props "
            "RETURN r",
            {"src": source, "tgt": target, "props": rel_props},
        )
        if not result.result_set:
            return None
        return {
            "source_id": source,
            "target_id": target,
            "story": story,
            "timestamp": ts,
            "relationship_id": rel_id,
            **props,
        }

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete an ``is_connected_to`` relationship by UUID. Returns True if found."""
        result = await self._graph.query(
            f"MATCH ()-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->() "
            "DELETE r RETURN count(r) AS cnt",
            {"rid": relationship_id},
        )
        if not result.result_set:
            return False
        return bool(result.result_set[0][0])

    async def update_relationship_props(self, relationship_id: str, **props) -> bool:
        """Merge *props* into an existing relationship. Returns True if found.

        The relationship_id, source, story, target, and timestamp are never
        changed — only the extra properties are updated.
        """
        result = await self._graph.query(
            f"MATCH ()-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->() "
            "SET r += $props RETURN count(r) AS cnt",
            {"rid": relationship_id, "props": props},
        )
        if not result.result_set:
            return False
        return bool(result.result_set[0][0])

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_composition(self) -> dict[str, int]:
        """Return node counts grouped by label (from the ``labels`` property)."""
        result = await self._graph.query("MATCH (n:Node) RETURN n.labels AS lbls")
        composition: dict[str, int] = {}
        for row in result.result_set:
            for label in (row[0] or []):
                composition[label] = composition.get(label, 0) + 1
        return composition

    async def get_taxonomy(self) -> dict[str, int]:
        """Return relationship counts grouped by story."""
        result = await self._graph.query(
            f"MATCH ()-[r:{REL_CONNECTED}]->() "
            "UNWIND r.stories AS story "
            "RETURN story, count(story) AS cnt"
        )
        taxonomy: dict[str, int] = {}
        for row in result.result_set:
            story: str = row[0] or "unknown"
            taxonomy[story] = taxonomy.get(story, 0) + row[1]
        return taxonomy

    async def dump_all_rels(self, path: str) -> int:
        """Dump all relationships to *path* in pipe-delimited quad format."""
        rels = await self.get_relationships()
        lines = [format_dump_line(r) for r in rels]
        with open(path, "w") as f:
            f.write("\n".join(lines))
        return len(rels)

    # ------------------------------------------------------------------
    # Identity / legacy helpers
    # ------------------------------------------------------------------

    async def link_is(self, node1_id: str, node2_id: str) -> None:
        """Create bidirectional ``is_the_same_as`` relationships."""
        await self._graph.query(
            f"MATCH (n1:Node {{nodeid: $n1}}), (n2:Node {{nodeid: $n2}}) "
            f"MERGE (n1)-[:{REL_IDENTITY}]->(n2) "
            f"MERGE (n2)-[:{REL_IDENTITY}]->(n1)",
            {"n1": node1_id, "n2": node2_id},
        )
