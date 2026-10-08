"""Async pytest tests for MemoryGoat.

MemoryGoat is the in-memory fallback backend — no live service required.
"""
import os
import pytest

from mojogoat.goatbases.memorygoat import MemoryGoat


@pytest.fixture
def goat():
    return MemoryGoat()


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_and_get_node(goat):
    node = await goat.add_node("alice", name="Alice", labels=["Person"])
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"
    assert node["labels"] == ["Person"]
    assert "created" in node and "updated" in node

    fetched = await goat.get_node("alice")
    assert fetched is not None
    assert fetched["nodeid"] == "alice"
    assert fetched["name"] == "Alice"


@pytest.mark.asyncio
async def test_update_node_merges(goat):
    await goat.add_node("bob", name="Bob", labels=["Person"])
    updated = await goat.add_node("bob", title="Engineer")
    assert updated["name"] == "Bob"
    assert updated["title"] == "Engineer"


@pytest.mark.asyncio
async def test_get_nodes_returns_all(goat):
    await goat.add_node("n1", labels=["X"])
    await goat.add_node("n2", labels=["Y"])
    nodes = await goat.get_nodes()
    assert {n["nodeid"] for n in nodes} == {"n1", "n2"}


@pytest.mark.asyncio
async def test_get_nodes_by_label(goat):
    await goat.add_node("p1", labels=["Person"])
    await goat.add_node("p2", labels=["Person"])
    await goat.add_node("c1", labels=["Company"])
    assert len(await goat.get_nodes_by_label("Person")) == 2
    assert len(await goat.get_nodes_by_label("Company")) == 1


@pytest.mark.asyncio
async def test_get_nonexistent_node_returns_none(goat):
    assert await goat.get_node("ghost") is None


@pytest.mark.asyncio
async def test_delete_node(goat):
    await goat.add_node("del_me")
    assert await goat.delete_node("del_me") is True
    assert await goat.get_node("del_me") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_node(goat):
    assert await goat.delete_node("nope") is False


@pytest.mark.asyncio
async def test_delete_node_removes_relationships(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.create_relationship("a", "b", "KNOWS")
    await goat.delete_node("a")
    assert await goat.get_relationships() == []


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_get_relationship(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS")
    assert rel is not None
    assert rel["source_id"] == "a"
    assert rel["target_id"] == "b"
    assert rel["story"] == "KNOWS"
    assert len(rel["relationship_id"]) == 36
    assert "T" in rel["timestamp"]

    rels = await goat.get_relationships()
    assert len(rels) == 1
    assert rels[0]["relationship_id"] == rel["relationship_id"]


@pytest.mark.asyncio
async def test_create_relationship_with_props(goat):
    await goat.add_node("x")
    await goat.add_node("y")
    rel = await goat.create_relationship("x", "y", "LINKED", state="active", weight=3)
    assert rel["state"] == "active"
    assert rel["weight"] == 3
    rels = await goat.get_relationships()
    assert rels[0]["state"] == "active"
    assert rels[0]["weight"] == 3


@pytest.mark.asyncio
async def test_create_relationship_missing_node_returns_none(goat):
    await goat.add_node("src")
    assert await goat.create_relationship("src", "missing", "KNOWS") is None


@pytest.mark.asyncio
async def test_relationship_filters(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.add_node("c")
    await goat.create_relationship("a", "b", "KNOWS")
    await goat.create_relationship("a", "c", "LIKES")

    assert len(await goat.get_relationships(source="a")) == 2
    assert len(await goat.get_relationships(target="b")) == 1
    by_story = await goat.get_relationships(story="KNOWS")
    assert len(by_story) == 1
    assert by_story[0]["target_id"] == "b"


@pytest.mark.asyncio
async def test_get_relationship_found(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS", state="pending")
    rid = rel["relationship_id"]

    fetched = await goat.get_relationship(rid)
    assert fetched is not None
    assert fetched["relationship_id"] == rid
    assert fetched["state"] == "pending"


@pytest.mark.asyncio
async def test_get_relationship_not_found(goat):
    assert await goat.get_relationship("00000000-0000-0000-0000-000000000000") is None


@pytest.mark.asyncio
async def test_get_relationships_props_filter(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.add_node("c")
    await goat.create_relationship("a", "b", "KNOWS", state="pending")
    await goat.create_relationship("a", "c", "KNOWS", state="confirmed")

    pending = await goat.get_relationships(props={"state": "pending"})
    assert len(pending) == 1
    assert pending[0]["target_id"] == "b"


@pytest.mark.asyncio
async def test_get_relationships_limit(goat):
    await goat.add_node("src")
    for i in range(5):
        await goat.add_node(f"tgt{i}")
        await goat.create_relationship("src", f"tgt{i}", "LINKED")
    assert len(await goat.get_relationships(limit=3)) == 3


@pytest.mark.asyncio
async def test_delete_relationship(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS")
    rid = rel["relationship_id"]
    assert await goat.delete_relationship(rid) is True
    assert await goat.get_relationships() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_relationship(goat):
    assert await goat.delete_relationship("00000000-0000-0000-0000-000000000000") is False


@pytest.mark.asyncio
async def test_update_relationship_props_merges(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS", state="pending")
    rid = rel["relationship_id"]

    assert await goat.update_relationship_props(rid, state="confirmed", score=42) is True

    rels = await goat.get_relationships()
    r = rels[0]
    assert r["state"] == "confirmed"
    assert r["score"] == 42
    assert r["story"] == "KNOWS"
    assert r["source_id"] == "a"


@pytest.mark.asyncio
async def test_update_relationship_props_not_found(goat):
    assert await goat.update_relationship_props(
        "00000000-0000-0000-0000-000000000000", state="x"
    ) is False


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_composition(goat):
    await goat.add_node("p1", labels=["Person"])
    await goat.add_node("p2", labels=["Person"])
    await goat.add_node("c1", labels=["Company"])
    comp = await goat.get_composition()
    assert comp["Person"] == 2
    assert comp["Company"] == 1


@pytest.mark.asyncio
async def test_get_taxonomy(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.add_node("c")
    await goat.create_relationship("a", "b", "KNOWS")
    await goat.create_relationship("a", "c", "KNOWS")
    await goat.create_relationship("b", "c", "LIKES")
    tax = await goat.get_taxonomy()
    assert tax["KNOWS"] == 2
    assert tax["LIKES"] == 1


@pytest.mark.asyncio
async def test_dump_all_rels(goat, tmp_path):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.create_relationship("a", "b", "KNOWS")
    path = str(tmp_path / "dump.txt")
    count = await goat.dump_all_rels(path)
    assert count == 1
    assert os.path.exists(path)
    assert "a|KNOWS|b" in open(path).read()


@pytest.mark.asyncio
async def test_iso8601_timestamp(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS")
    assert "T" in rel["timestamp"]
