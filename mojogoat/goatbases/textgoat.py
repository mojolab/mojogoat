import os
import json
import re
import secrets
import string
from datetime import datetime
from uuid import uuid5, NAMESPACE_URL

import aiofiles

_ID_ALPHABET = string.ascii_letters + string.digits  # base-62


def _short_id(n: int = 10) -> str:
    """Return a random *n*-character base-62 string."""
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(n))

from .base import GoatBase, REL_IDENTITY


class TextGoat(GoatBase):
    def __init__(self, goatconfig):
        self.config = goatconfig
        self.goatpath = goatconfig['goatpath']
        self.goatname = goatconfig['goatname']

        os.makedirs(self.goatpath, exist_ok=True)
        os.makedirs(os.path.join(self.goatpath, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(self.goatpath, "snapshots"), exist_ok=True)

        newgrass_path = os.path.join(self.goatpath, "newgrass.gq")
        if not os.path.exists(newgrass_path):
            with open(newgrass_path, 'w') as f:
                f.write("")

        goatrels_path = os.path.join(self.goatpath, "goatrels.gq")
        if not os.path.exists(goatrels_path):
            with open(goatrels_path, 'w') as f:
                f.write("")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _node_path(self, nodeid: str) -> str:
        return os.path.join(self.goatpath, "nodes", nodeid)

    def _rel_id_from_line(self, line: str, parts: list[str]) -> str:
        """Return the relationship UUID for a .gq line.

        New format (5+ fields): parts[4] is the stored UUID.
        Old format (4 fields):  derive a stable UUID from the line content.
        """
        if len(parts) >= 5 and parts[4]:
            return parts[4]
        return str(uuid5(NAMESPACE_URL, "|".join(parts[:4])))

    async def _read_rel_lines(self) -> list[str]:
        """Return raw (non-empty) lines from the current snapshot file."""
        ref_path = os.path.join(self.goatpath, "goatrels.gq")
        async with aiofiles.open(ref_path, "r") as f:
            relfile = (await f.read()).strip()
        if not relfile:
            return []
        snapshot_path = os.path.join(self.goatpath, relfile)
        if not os.path.exists(snapshot_path):
            return []
        async with aiofiles.open(snapshot_path, "r") as f:
            content = await f.read()
        return [ln for ln in content.split("\n") if ln.strip()]

    async def _write_rel_lines(self, lines: list[str]) -> None:
        """Persist *lines* as a new snapshot and update the reference file."""
        snapshot_name = f"mojogoat-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}"
        snapshot_path = os.path.join(self.goatpath, "snapshots", snapshot_name)
        ref_path = os.path.join(self.goatpath, "goatrels.gq")
        async with aiofiles.open(snapshot_path, "w") as f:
            await f.write("\n".join(lines))
        async with aiofiles.open(ref_path, "w") as f:
            await f.write(os.path.join("snapshots", snapshot_name))

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    async def add_node(self, nodeid: str, **kwargs) -> dict:
        """Create or update a node."""
        node_data = kwargs.copy()
        node_data['nodeid'] = nodeid

        # Normalise labels
        raw_labels = node_data.get('labels') or node_data.get('nodelabels')
        if raw_labels is not None:
            if isinstance(raw_labels, list):
                node_data['labels'] = raw_labels
            else:
                node_data['labels'] = [l.strip() for l in str(raw_labels).split(',')]

        # Timestamps
        now = datetime.now().isoformat()
        node_data.setdefault('created', now)
        node_data['updated'] = now

        node_path = self._node_path(nodeid)

        # Merge with existing data if the node already exists
        if os.path.exists(node_path):
            try:
                async with aiofiles.open(node_path, 'r') as f:
                    content = await f.read()
                if content.strip():
                    existing = json.loads(content)
                    existing.update(node_data)
                    node_data = existing
            except (json.JSONDecodeError, Exception):
                pass

        async with aiofiles.open(node_path, 'w') as f:
            await f.write(json.dumps(node_data, indent=2))

        return node_data

    async def get_nodes(self) -> list[dict]:
        """Return all nodes."""
        nodes = []
        nodes_dir = os.path.join(self.goatpath, "nodes")
        if not os.path.exists(nodes_dir):
            return nodes

        for filename in os.listdir(nodes_dir):
            file_path = os.path.join(nodes_dir, filename)
            if os.path.isdir(file_path) or filename.startswith('.'):
                continue
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                if not content.strip():
                    continue
                node_data = json.loads(content)
                node_data.setdefault('nodeid', filename)
                nodes.append(node_data)
            except (json.JSONDecodeError, Exception):
                pass

        return nodes

    async def get_node(self, nodeid: str) -> dict | None:
        """Return a single node by ID, or None if not found."""
        if not nodeid:
            return None
        node_path = self._node_path(nodeid)
        if not os.path.exists(node_path):
            return None
        try:
            async with aiofiles.open(node_path, 'r') as f:
                content = await f.read()
            if not content.strip():
                return None
            node_data = json.loads(content)
            node_data.setdefault('nodeid', nodeid)
            return node_data
        except (json.JSONDecodeError, Exception):
            return None

    async def get_nodes_by_label(self, label: str) -> list[dict]:
        """Return all nodes carrying *label*."""
        matching = []
        for node in await self.get_nodes():
            node_labels: list[str] = []
            for key in ('labels', 'nodelabels'):
                val = node.get(key)
                if val:
                    if isinstance(val, list):
                        node_labels.extend(val)
                    else:
                        node_labels.append(str(val))
            if label in node_labels:
                matching.append(node)
        return matching

    async def delete_node(self, nodeid: str) -> bool:
        """Delete a node file. Returns True on success."""
        if not nodeid:
            return False
        node_path = self._node_path(nodeid)
        if not os.path.exists(node_path) or not os.path.isfile(node_path):
            return False
        try:
            os.remove(node_path)
            return True
        except Exception:
            return False

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
        """Return relationships, optionally filtered by source / target / story / props."""
        relationships = []
        try:
            lines = await self._read_rel_lines()
        except Exception:
            return relationships

        skipped = 0
        for line in lines:
            parts = line.split("|")
            if len(parts) < 3:
                continue
            ts = parts[3] if len(parts) >= 4 else datetime.now().isoformat()
            rel_id = self._rel_id_from_line(line, parts)
            extra: dict = {}
            if len(parts) >= 6:
                try:
                    extra = json.loads(parts[5])
                except (json.JSONDecodeError, ValueError):
                    pass

            reldict: dict = {
                "source_id": parts[0],
                "story": parts[1],
                "target_id": parts[2],
                "timestamp": ts,
                "relationship_id": rel_id,
                **extra,
            }

            if (source is None or reldict["source_id"] == source) and \
               (target is None or reldict["target_id"] == target) and \
               (story is None or reldict["story"] == story):
                if props and not all(reldict.get(k) == v for k, v in props.items()):
                    continue
                if offset is not None and skipped < offset:
                    skipped += 1
                    continue
                relationships.append(reldict)
                if limit is not None and len(relationships) >= limit:
                    break

        return relationships

    async def get_relationship(self, relationship_id: str) -> dict | None:
        """Return a single relationship by UUID, or None if not found."""
        for rel in await self.get_relationships():
            if rel.get("relationship_id") == relationship_id:
                return rel
        return None

    async def create_relationship(
        self,
        source: str,
        target: str,
        story: str,
        **props,
    ) -> dict | None:
        """Create a relationship quad and return its dict.

        Any extra keyword arguments are stored as additional properties.
        """
        try:
            if not await self.get_node(source) or not await self.get_node(target):
                return None

            rel_id = f"{self.goatname}:{_short_id()}"
            ts = datetime.now().isoformat()
            line = f"{source}|{story}|{target}|{ts}|{rel_id}"
            if props:
                line += f"|{json.dumps(props, separators=(',', ':'))}"

            lines = await self._read_rel_lines()
            if line not in lines:
                lines.append(line)
            await self._write_rel_lines(lines)

            return {
                "source_id": source,
                "target_id": target,
                "story": story,
                "timestamp": ts,
                "relationship_id": rel_id,
                **props,
            }
        except Exception:
            return None

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship by its UUID. Returns True on success."""
        try:
            lines = await self._read_rel_lines()
            new_lines = []
            found = False
            for line in lines:
                parts = line.split("|")
                rid = self._rel_id_from_line(line, parts)
                if rid == relationship_id:
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                return False
            await self._write_rel_lines(new_lines)
            return True
        except Exception:
            return False

    async def update_relationship_props(self, relationship_id: str, **props) -> bool:
        """Merge *props* into an existing relationship. Returns True if found.

        The relationship_id, source, story, target, and timestamp are never
        changed — only the extra properties are updated.
        """
        try:
            lines = await self._read_rel_lines()
            new_lines = []
            found = False
            for line in lines:
                parts = line.split("|")
                rid = self._rel_id_from_line(line, parts)
                if rid == relationship_id:
                    found = True
                    existing_props: dict = {}
                    if len(parts) >= 6:
                        try:
                            existing_props = json.loads("|".join(parts[5:]))
                        except (json.JSONDecodeError, ValueError):
                            pass
                    existing_props.update(props)
                    base = "|".join(parts[:5])
                    line = f"{base}|{json.dumps(existing_props, separators=(',', ':'))}"
                new_lines.append(line)
            if not found:
                return False
            await self._write_rel_lines(new_lines)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_composition(self) -> dict[str, int]:
        """Return a count of nodes by label."""
        composition: dict[str, int] = {}
        for node in await self.get_nodes():
            for label in node.get('labels', []):
                composition[label] = composition.get(label, 0) + 1
        return composition

    async def get_taxonomy(self) -> dict[str, int]:
        """Return a count of relationships by story type."""
        taxonomy: dict[str, int] = {}
        for rel in await self.get_relationships():
            story = rel['story']
            taxonomy[story] = taxonomy.get(story, 0) + 1
        return taxonomy

    async def compact(self) -> int:
        """Rewrite the current snapshot to a fresh file; delete all orphaned snapshots.

        Returns the number of relationships preserved.
        """
        lines = await self._read_rel_lines()
        await self._write_rel_lines(lines)

        ref_path = os.path.join(self.goatpath, 'goatrels.gq')
        async with aiofiles.open(ref_path, 'r') as f:
            current_rel = (await f.read()).strip()
        current_name = os.path.basename(current_rel)

        snapshots_dir = os.path.join(self.goatpath, 'snapshots')
        for fname in os.listdir(snapshots_dir):
            if fname != current_name:
                try:
                    os.remove(os.path.join(snapshots_dir, fname))
                except Exception:
                    pass

        return len(lines)

    async def dump_all_rels(self, filename: str) -> int:
        """Dump all relationships to *filename* in pipe-delimited format."""
        rels = await self.get_relationships()
        lines = [
            f"{r['source_id']}|{r['story']}|{r['target_id']}|{r['timestamp']}"
            for r in rels
        ]
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        async with aiofiles.open(filename, "w") as f:
            await f.write("\n".join(lines))
        return len(rels)

    async def link_is(self, node1_id: str, node2_id: str) -> None:
        """Create bidirectional is_the_same_as relationships between two nodes."""
        await self.create_relationship(node1_id, node2_id, REL_IDENTITY)
        await self.create_relationship(node2_id, node1_id, REL_IDENTITY)

    # ------------------------------------------------------------------
    # Legacy / feed interface (kept sync — not part of async migration)
    # ------------------------------------------------------------------

    def ask_goat(self, query: str):
        if re.match(r"searchrels", query):
            tokens = query.replace("searchrels", "").split()
            with open(os.path.join(self.goatpath, "goatrels.gq"), "r") as f:
                latestfile = f.read().strip()
            curfile = os.path.join(self.goatpath, latestfile)
            cmd = f"cat {curfile} " + " ".join(f"| grep {t}" for t in tokens)
            lines = os.popen(cmd).read().strip().split("\n")
            return [ln for ln in lines if ln]
        if re.match(r"shownewrels", query):
            tokens = query.replace("shownewrels", "").split()
            curfile = os.path.join(self.goatpath, "newgrass.gq")
            cmd = f"cat {curfile} " + " ".join(f"| grep {t}" for t in tokens if t)
            lines = os.popen(cmd).read().strip().split("\n")
            return lines[:50]
        if re.match(r"searchnode", query):
            tokens = query.replace("searchnode", "").split()
            results = []
            for token in tokens:
                cmd = f"find {os.path.join(self.goatpath, 'nodes')} -name '*{token}*'"
                results.extend(
                    os.path.split(ln)[1]
                    for ln in os.popen(cmd).read().strip().split("\n")
                )
            return results
        if re.match(r"getnode", query):
            nodeid = query.replace("getnode", "").strip()
            path = os.path.join(self.goatpath, "nodes", nodeid)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.dumps(json.loads(f.read()))

    def feed_goat(self, feed: str):
        feedlines = feed.strip().split("\n")
        quadlist = []
        for line in feedlines:
            tokens = line.split(" ")
            if len(tokens) < 3:
                continue
            source = tokens[0]
            target = tokens[-1]
            story = line.replace(source, "").replace(target, "").strip()
            rel_id = str(uuid4())
            ts = datetime.now().isoformat()
            quadlist.append(f"{source}|{story}|{target}|{ts}|{rel_id}")
        with open(os.path.join(self.goatpath, "newgrass.gq"), 'a') as f:
            f.write("\n" + "\n".join(quadlist))
        return quadlist

    def tell_goat(self, tell: str, apply_to=None):
        if re.match(r"pull", tell):
            try:
                return os.popen(f"cd {self.goatpath} && git pull && cd").read().strip()
            except Exception as e:
                return str(e)
        if re.match(r"push", tell):
            try:
                return os.popen(
                    f"cd {self.goatpath} && git add * && git commit -a -m 'auto commit' && git push && cd"
                ).read().strip()
            except Exception as e:
                return str(e)
        if re.match(r"dropline", tell):
            out = "Really drop lines?\n"
            if apply_to is not None:
                out += apply_to
            return out

    # ------------------------------------------------------------------
    # Legacy aliases
    # ------------------------------------------------------------------

    async def all_nodes(self) -> list[dict]:
        return await self.get_nodes()

    async def all_rels(self) -> list[dict]:
        return await self.get_relationships()

    async def add_rels(self, newrels: list[str]) -> str:
        """Append raw pipe-delimited relationship strings (legacy import path)."""
        try:
            lines = await self._read_rel_lines()
            combined = list(set(lines + newrels))
            await self._write_rel_lines(combined)
            return f"Added {len(newrels)} relationships. Total: {len(combined)}"
        except Exception as e:
            return str(e)
