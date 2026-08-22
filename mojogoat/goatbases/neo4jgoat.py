import json
from datetime import datetime
from uuid import uuid4

from neo4j import AsyncGraphDatabase

from .base import GoatBase, REL_CONNECTED, REL_IDENTITY, format_dump_line


class Neo4jGoat(GoatBase):
    """Async Neo4j backend using the official neo4j driver."""

    def __init__(self, configjson: str) -> None:
        with open(configjson) as f:
            goatconfig = json.load(f)
        self.driver = AsyncGraphDatabase.driver(
            goatconfig['url'],
            auth=(goatconfig['database'], goatconfig['password']),
        )

    @classmethod
    def from_config(cls, configjson: str) -> "Neo4jGoat":
        """Construct from a JSON config file path — alias for the default constructor."""
        return cls(configjson)

    async def close(self) -> None:
        await self.driver.close()

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    async def add_node(self, nodeid: str, **kwargs) -> dict:
        """Create or update a node. Returns the node as a dict."""
        kwargs['nodeid'] = nodeid
        kwargs.setdefault('created', datetime.now().isoformat())
        kwargs['updated'] = datetime.now().isoformat()

        async with self.driver.session() as session:
            existing = await session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN n", nodeid=nodeid
            )
            record = await existing.single()
            if record:
                await session.run(
                    "MATCH (n {nodeid: $nodeid}) SET n += $props",
                    nodeid=nodeid, props=kwargs,
                )
            else:
                label = kwargs.get('labels', ['Node'])
                label = label[0] if isinstance(label, list) and label else 'Node'
                await session.run(
                    f"CREATE (n:{label} {{nodeid: $nodeid}}) SET n += $props",
                    nodeid=nodeid, props=kwargs,
                )
        return kwargs

    async def get_node(self, nodeid: str) -> dict | None:
        """Return a node dict by ID, or None."""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN n, labels(n) AS lbls",
                nodeid=nodeid,
            )
            record = await result.single()
            if not record:
                return None
            node = dict(record["n"])
            node['labels'] = list(record["lbls"])
            return node

    async def get_nodes(self) -> list[dict]:
        """Return all nodes."""
        nodes = []
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n) RETURN n, labels(n) AS lbls"
            )
            async for record in result:
                node = dict(record["n"])
                node['labels'] = list(record["lbls"])
                nodes.append(node)
        return nodes

    async def get_nodes_by_label(self, label: str) -> list[dict]:
        """Return all nodes whose ``labels`` property contains *label*."""
        nodes = []
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n) WHERE $label IN n.labels RETURN n, labels(n) AS lbls",
                label=label,
            )
            async for record in result:
                node = dict(record["n"])
                node['labels'] = list(record["lbls"])
                nodes.append(node)
        return nodes

    async def delete_node(self, nodeid: str) -> bool:
        """Delete a node and its relationships. Returns True if found."""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {nodeid: $nodeid}) DETACH DELETE n RETURN count(n) AS cnt",
                nodeid=nodeid,
            )
            record = await result.single()
            return bool(record and record["cnt"] > 0)

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
        conditions = []
        params: dict = {}
        if source:
            conditions.append("n.nodeid = $source")
            params['source'] = source
        if target:
            conditions.append("m.nodeid = $target")
            params['target'] = target
        if story:
            conditions.append("$story IN r.stories")
            params['story'] = story
        if props:
            for k, v in props.items():
                param_name = f"prop_{k}"
                conditions.append(f"r.{k} = ${param_name}")
                params[param_name] = v

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        skip_clause = f" SKIP {int(offset)}" if offset is not None else ""
        limit_clause = f" LIMIT {int(limit)}" if limit is not None else ""
        query = (
            f"MATCH (n)-[r:{REL_CONNECTED}]->(m){where_clause} "
            "RETURN n.nodeid AS src, r.stories AS stories, m.nodeid AS tgt, "
            f"r.timestamp AS ts, r.relationship_id AS rid, properties(r) AS props{skip_clause}{limit_clause}"
        )

        rels = []
        async with self.driver.session() as session:
            result = await session.run(query, **params)
            async for record in result:
                stories = record["stories"] or []
                extra = {
                    k: v for k, v in (record["props"] or {}).items()
                    if k not in ("stories", "timestamp", "relationship_id")
                }
                rels.append({
                    "source_id": record["src"],
                    "story": stories[0] if stories else "",
                    "target_id": record["tgt"],
                    "timestamp": record["ts"],
                    "relationship_id": record["rid"],
                    **extra,
                })
        return rels

    async def get_relationship(self, relationship_id: str) -> dict | None:
        """Return a single relationship by UUID, or None if not found."""
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH (n)-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->(m) "
                "RETURN n.nodeid AS src, r.stories AS stories, m.nodeid AS tgt, "
                "r.timestamp AS ts, r.relationship_id AS rid, properties(r) AS props",
                rid=relationship_id,
            )
            record = await result.single()
            if not record:
                return None
            stories = record["stories"] or []
            extra = {
                k: v for k, v in (record["props"] or {}).items()
                if k not in ("stories", "timestamp", "relationship_id")
            }
            return {
                "source_id": record["src"],
                "story": stories[0] if stories else "",
                "target_id": record["tgt"],
                "timestamp": record["ts"],
                "relationship_id": record["rid"],
                **extra,
            }

    async def create_relationship(
        self,
        source: str,
        target: str,
        story: str,
        **props,
    ) -> dict | None:
        """Create an is_connected_to relationship between two nodes."""
        rel_id = str(uuid4())
        ts = datetime.now().isoformat()
        rel_props = {
            "stories": [story],
            "timestamp": ts,
            "relationship_id": rel_id,
            **props,
        }
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {nodeid: $src}), (m {nodeid: $tgt}) "
                f"CREATE (n)-[r:{REL_CONNECTED}]->(m) SET r += $props "
                "RETURN r",
                src=source, tgt=target, props=rel_props,
            )
            record = await result.single()
            if not record:
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
        """Delete a relationship by its UUID property."""
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH ()-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->() "
                "DELETE r RETURN count(r) AS cnt",
                rid=relationship_id,
            )
            record = await result.single()
            return bool(record and record["cnt"] > 0)

    async def update_relationship_props(self, relationship_id: str, **props) -> bool:
        """Merge *props* into an existing relationship. Returns True if found.

        The relationship_id, source, story, target, and timestamp are never
        changed — only the extra properties are updated.
        """
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH ()-[r:{REL_CONNECTED} {{relationship_id: $rid}}]->() "
                "SET r += $props RETURN count(r) AS cnt",
                rid=relationship_id, props=props,
            )
            record = await result.single()
            return bool(record and record["cnt"] > 0)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_composition(self) -> dict[str, int]:
        """Return node counts grouped by label."""
        composition: dict[str, int] = {}
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n) RETURN labels(n) AS lbls, count(n) AS cnt"
            )
            async for record in result:
                for label in record["lbls"]:
                    composition[label] = composition.get(label, 0) + record["cnt"]
        return composition

    async def get_taxonomy(self) -> dict[str, int]:
        """Return relationship counts grouped by story."""
        taxonomy: dict[str, int] = {}
        async with self.driver.session() as session:
            result = await session.run(
                f"MATCH ()-[r:{REL_CONNECTED}]->() "
                "UNWIND r.stories AS story "
                "RETURN story, count(story) AS cnt"
            )
            async for record in result:
                story = record["story"] or "unknown"
                taxonomy[story] = taxonomy.get(story, 0) + record["cnt"]
        return taxonomy

    async def dump_all_rels(self, path: str) -> int:
        """Dump all relationships to *path* in pipe-delimited format."""
        rels = await self.get_relationships()
        lines = [format_dump_line(r) for r in rels]
        with open(path, "w") as f:
            f.write("\n".join(lines))
        return len(rels)

    # ------------------------------------------------------------------
    # Legacy helpers (kept for mojogoatsync / test scripts)
    # ------------------------------------------------------------------

    async def link(
        self,
        x_nodeid: str,
        y_nodeid: str,
        storyline: str,
        adddate: str,
    ) -> None:
        """Low-level: merge an is_connected_to relationship."""
        async with self.driver.session() as session:
            await session.run(
                "MATCH (x {nodeid: $x}), (y {nodeid: $y}) "
                f"MERGE (x)-[r:{REL_CONNECTED}]->(y) "
                "SET r.stories = [$story], r.timestamp = $ts, r.updatedate = $upd",
                x=x_nodeid, y=y_nodeid, story=storyline,
                ts=adddate, upd=datetime.now().isoformat(),
            )

    async def link_is(self, node1_id: str, node2_id: str) -> None:
        async with self.driver.session() as session:
            await session.run(
                "MATCH (n1 {nodeid: $n1}), (n2 {nodeid: $n2}) "
                f"MERGE (n1)-[:{REL_IDENTITY}]->(n2) "
                f"MERGE (n2)-[:{REL_IDENTITY}]->(n1)",
                n1=node1_id, n2=node2_id,
            )

    async def get_node_dict(self, nodeid: str) -> dict | None:
        """Alias for get_node() — kept for backward compatibility."""
        return await self.get_node(nodeid)

    async def update_labels(self, nodeid: str, labels: list[str]) -> None:
        label_str = ":".join(labels)
        async with self.driver.session() as session:
            await session.run(
                f"MATCH (n {{nodeid: $nodeid}}) SET n:{label_str}",
                nodeid=nodeid,
            )

    async def get_labels(self, nodeid: str) -> list[str]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {nodeid: $nodeid}) RETURN labels(n) AS lbls",
                nodeid=nodeid,
            )
            record = await result.single()
            return list(record["lbls"]) if record else []
