"""Async pytest tests for TextGoat."""
import json
import os
import pytest

from mojogoat.goatbases.textgoat import TextGoat


@pytest.fixture
def goat(tmp_path):
    config = {
        "goatpath": str(tmp_path / "testgoat"),
        "goatname": "testgoat",
    }
    return TextGoat(config)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_and_get_node(goat):
    node = await goat.add_node("alice", name="Alice", labels=["Person"])
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"
    assert node["labels"] == ["Person"]
    assert "created" in node
    assert "updated" in node

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
    ids = {n["nodeid"] for n in nodes}
    assert ids == {"n1", "n2"}


@pytest.mark.asyncio
async def test_get_nodes_by_label(goat):
    await goat.add_node("p1", labels=["Person"])
    await goat.add_node("p2", labels=["Person"])
    await goat.add_node("c1", labels=["Company"])
    people = await goat.get_nodes_by_label("Person")
    assert len(people) == 2
    companies = await goat.get_nodes_by_label("Company")
    assert len(companies) == 1


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
    assert "relationship_id" in rel
    # UUID format
    assert len(rel["relationship_id"]) == 36

    rels = await goat.get_relationships()
    assert len(rels) == 1
    assert rels[0]["relationship_id"] == rel["relationship_id"]


@pytest.mark.asyncio
async def test_create_relationship_with_props(goat):
    await goat.add_node("x")
    await goat.add_node("y")
    rel = await goat.create_relationship("x", "y", "LINKED_TO", state="active", weight=3)
    assert rel["state"] == "active"
    assert rel["weight"] == 3

    rels = await goat.get_relationships()
    assert rels[0]["state"] == "active"
    assert rels[0]["weight"] == 3


@pytest.mark.asyncio
async def test_create_relationship_missing_node_returns_none(goat):
    await goat.add_node("src")
    result = await goat.create_relationship("src", "missing", "KNOWS")
    assert result is None


@pytest.mark.asyncio
async def test_relationship_filters(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.add_node("c")
    await goat.create_relationship("a", "b", "KNOWS")
    await goat.create_relationship("a", "c", "LIKES")

    by_source = await goat.get_relationships(source="a")
    assert len(by_source) == 2

    by_target = await goat.get_relationships(target="b")
    assert len(by_target) == 1

    by_story = await goat.get_relationships(story="KNOWS")
    assert len(by_story) == 1
    assert by_story[0]["target_id"] == "b"


@pytest.mark.asyncio
async def test_delete_relationship(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS")
    rid = rel["relationship_id"]

    assert await goat.delete_relationship(rid) is True
    rels = await goat.get_relationships()
    assert len(rels) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_relationship(goat):
    assert await goat.delete_relationship("00000000-0000-0000-0000-000000000000") is False


@pytest.mark.asyncio
async def test_update_relationship_props_merges(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS", state="pending")
    rid = rel["relationship_id"]

    result = await goat.update_relationship_props(rid, state="confirmed", score=42)
    assert result is True

    rels = await goat.get_relationships()
    assert len(rels) == 1
    assert rels[0]["relationship_id"] == rid   # ID preserved
    assert rels[0]["state"] == "confirmed"      # updated
    assert rels[0]["score"] == 42               # new prop added
    assert rels[0]["story"] == "KNOWS"          # unchanged
    assert rels[0]["source_id"] == "a"          # unchanged


@pytest.mark.asyncio
async def test_update_relationship_props_not_found(goat):
    result = await goat.update_relationship_props(
        "00000000-0000-0000-0000-000000000000", state="confirmed"
    )
    assert result is False


@pytest.mark.asyncio
async def test_update_relationship_props_preserves_other_rels(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    await goat.add_node("c")
    rel1 = await goat.create_relationship("a", "b", "KNOWS", state="pending")
    rel2 = await goat.create_relationship("a", "c", "LIKES", state="pending")

    await goat.update_relationship_props(rel1["relationship_id"], state="confirmed")

    rels = await goat.get_relationships()
    by_id = {r["relationship_id"]: r for r in rels}
    assert by_id[rel1["relationship_id"]]["state"] == "confirmed"
    assert by_id[rel2["relationship_id"]]["state"] == "pending"  # untouched


@pytest.mark.asyncio
async def test_iso8601_timestamp(goat):
    await goat.add_node("a")
    await goat.add_node("b")
    rel = await goat.create_relationship("a", "b", "KNOWS")
    ts = rel["timestamp"]
    # ISO-8601: should contain 'T' separator
    assert "T" in ts


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
    dump_path = str(tmp_path / "dump.txt")
    count = await goat.dump_all_rels(dump_path)
    assert count == 1
    assert os.path.exists(dump_path)
    content = open(dump_path).read()
    assert "a|KNOWS|b" in content
