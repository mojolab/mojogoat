from datetime import datetime
from uuid import uuid4

import aiofiles

from .base import GoatBase, REL_IDENTITY


class MemoryGoat(GoatBase):
    """In-memory backend — no persistence, data lost on process restart.

    Useful as a last-resort fallback when no storage service is reachable,
    and for lightweight testing without touching the filesystem.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, dict] = {}
        self._rels: list[dict] = []

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    async def add_node(self, nodeid: str, **kwargs) -> dict:
        """Create or update a node. Returns the node as a dict."""
        now = datetime.now().isoformat()
        existing = dict(self._nodes.get(nodeid, {}))
        node = {**existing, **kwargs, "nodeid": nodeid}
        node.setdefault("created", now)
        node["updated"] = now
        if "labels" in node and not isinstance(node["labels"], list):
            node["labels"] = [str(node["labels"])]
        self._nodes[nodeid] = node
        return dict(node)

    async def get_node(self, nodeid: str) -> dict | None:
        """Return a node dict by ID, or None."""
        node = self._nodes.get(nodeid)
        return dict(node) if node else None

    async def get_nodes(self) -> list[dict]:
        """Return all nodes."""
        return [dict(n) for n in self._nodes.values()]

    async def get_nodes_by_label(self, label: str) -> list[dict]:
        """Return all nodes whose ``labels`` property contains *label*."""
        return [
            dict(n) for n in self._nodes.values()
            if label in n.get("labels", [])
        ]

    async def delete_node(self, nodeid: str) -> bool:
        """Delete a node and any relationships it participates in. Returns True if found."""
        if nodeid not in self._nodes:
            return False
        del self._nodes[nodeid]
        self._rels = [
            r for r in self._rels
            if r["source_id"] != nodeid and r["target_id"] != nodeid
        ]
        return True

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
        """Return relationships, optionally filtered."""
        results: list[dict] = []
        skipped = 0
        for rel in self._rels:
            if source is not None and rel["source_id"] != source:
                continue
            if target is not None and rel["target_id"] != target:
                continue
            if story is not None and rel["story"] != story:
                continue
            if props and not all(rel.get(k) == v for k, v in props.items()):
                continue
            if offset is not None and skipped < offset:
                skipped += 1
                continue
            results.append(dict(rel))
            if limit is not None and len(results) >= limit:
                break
        return results

    async def get_relationship(self, relationship_id: str) -> dict | None:
        """Return a single relationship by UUID, or None if not found."""
        for rel in self._rels:
            if rel["relationship_id"] == relationship_id:
                return dict(rel)
        return None

    async def create_relationship(
        self, source: str, target: str, story: str, **props
    ) -> dict | None:
        """Create a relationship. Returns None if either node doesn't exist."""
        if source not in self._nodes or target not in self._nodes:
            return None
        rel: dict = {
            "source_id": source,
            "story": story,
            "target_id": target,
            "timestamp": datetime.now().isoformat(),
            "relationship_id": str(uuid4()),
            **props,
        }
        self._rels.append(rel)
        return dict(rel)

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship by UUID. Returns True if found."""
        for i, rel in enumerate(self._rels):
            if rel["relationship_id"] == relationship_id:
                del self._rels[i]
                return True
        return False

    async def update_relationship_props(self, relationship_id: str, **props) -> bool:
        """Merge *props* into an existing relationship. Returns True if found."""
        for rel in self._rels:
            if rel["relationship_id"] == relationship_id:
                rel.update(props)
                return True
        return False

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_composition(self) -> dict[str, int]:
        """Return node counts grouped by label."""
        composition: dict[str, int] = {}
        for node in self._nodes.values():
            for label in node.get("labels", []):
                composition[label] = composition.get(label, 0) + 1
        return composition

    async def get_taxonomy(self) -> dict[str, int]:
        """Return relationship counts grouped by story."""
        taxonomy: dict[str, int] = {}
        for rel in self._rels:
            story = rel["story"]
            taxonomy[story] = taxonomy.get(story, 0) + 1
        return taxonomy

    async def dump_all_rels(self, path: str) -> int:
        """Dump all relationships to *path* in pipe-delimited quad format."""
        import os
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        lines = [
            f"{r['source_id']}|{r['story']}|{r['target_id']}|{r['timestamp']}"
            for r in self._rels
        ]
        async with aiofiles.open(path, "w") as f:
            await f.write("\n".join(lines))
        return len(self._rels)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    async def link_is(self, node1_id: str, node2_id: str) -> None:
        """Create bidirectional is_the_same_as relationships."""
        await self.create_relationship(node1_id, node2_id, REL_IDENTITY)
        await self.create_relationship(node2_id, node1_id, REL_IDENTITY)
