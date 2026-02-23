"""Async pytest tests for FalkorGoat.

Unit tests mock _graph.query so no live FalkorDB is required.
Integration tests are marked @pytest.mark.integration and skipped by default:
    uv run pytest test/ -m "not integration"
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from mojogoat.goatbases.falkorgoat import FalkorGoat


# ---------------------------------------------------------------------------
# Helpers: build mock FalkorDB result objects
# ---------------------------------------------------------------------------

def make_result(*rows):
    """Build a mock QueryResult with the given rows."""
    r = MagicMock()
    r.result_set = list(rows)
    return r


def make_node(properties: dict, labels: list | None = None):
    """Build a mock FalkorDB Node object."""
    n = MagicMock()
    n.properties = properties
    n.labels = labels or ["Node"]
    return n


def make_edge(properties: dict, relation: str = "is_connected_to"):
    """Build a mock FalkorDB Edge object."""
    e = MagicMock()
    e.properties = properties
    e.relation = relation
    return e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_graph():
    g = MagicMock()
    g.query = AsyncMock()
    return g


@pytest.fixture
def goat(mock_graph):
    return FalkorGoat.from_graph(mock_graph)


# ---------------------------------------------------------------------------
# Node CRUD — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_node_returns_dict(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    node = await goat.add_node("alice", name="Alice", labels=["Person"])
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"
    assert node["labels"] == ["Person"]
    assert "created" in node and "updated" in node
    mock_graph.query.assert_called_once()
    cypher = mock_graph.query.call_args[0][0]
    assert "MERGE" in cypher
    assert "nodeid" in cypher


@pytest.mark.asyncio
async def test_add_node_iso8601_timestamps(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    node = await goat.add_node("bob")
    assert "T" in node["created"]
    assert "T" in node["updated"]


@pytest.mark.asyncio
async def test_get_node_found(goat, mock_graph):
    mock_graph.query.return_value = make_result(
        [make_node({"nodeid": "alice", "name": "Alice", "labels": ["Person"]})]
    )
    node = await goat.get_node("alice")
    assert node is not None
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"


@pytest.mark.asyncio
async def test_get_node_not_found(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    assert await goat.get_node("ghost") is None


@pytest.mark.asyncio
async def test_get_nodes(goat, mock_graph):
    mock_graph.query.return_value = make_result(
        [make_node({"nodeid": "a", "labels": ["X"]})],
        [make_node({"nodeid": "b", "labels": ["Y"]})],
    )
    nodes = await goat.get_nodes()
    assert len(nodes) == 2
    assert {n["nodeid"] for n in nodes} == {"a", "b"}


@pytest.mark.asyncio
async def test_get_nodes_by_label_passes_label_param(goat, mock_graph):
    mock_graph.query.return_value = make_result(
        [make_node({"nodeid": "p1", "labels": ["Person"]})]
    )
    nodes = await goat.get_nodes_by_label("Person")
    assert len(nodes) == 1
    params = mock_graph.query.call_args[0][1]
    assert params["label"] == "Person"
    cypher = mock_graph.query.call_args[0][0]
    assert "IN n.labels" in cypher


@pytest.mark.asyncio
async def test_delete_node_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([1])
    assert await goat.delete_node("alice") is True
    cypher = mock_graph.query.call_args[0][0]
    assert "DETACH DELETE" in cypher


@pytest.mark.asyncio
async def test_delete_node_not_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([0])
    assert await goat.delete_node("ghost") is False


# ---------------------------------------------------------------------------
# Relationship CRUD — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_relationship_uses_is_connected_to(goat, mock_graph):
    rel_props = {
        "stories": ["KNOWS"],
        "timestamp": "2026-02-23T10:00:00",
        "relationship_id": "some-uuid",
    }
    mock_graph.query.return_value = make_result(
        [make_edge(rel_props)]
    )
    rel = await goat.create_relationship("a", "b", "KNOWS")
    assert rel is not None
    cypher = mock_graph.query.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "CREATE" in cypher


@pytest.mark.asyncio
async def test_create_relationship_uuid_v4(goat, mock_graph):
    mock_graph.query.return_value = make_result([make_edge({})])
    rel = await goat.create_relationship("a", "b", "KNOWS")
    rid = rel["relationship_id"]
    assert len(rid) == 36
    assert rid.count("-") == 4


@pytest.mark.asyncio
async def test_create_relationship_iso8601_timestamp(goat, mock_graph):
    mock_graph.query.return_value = make_result([make_edge({})])
    rel = await goat.create_relationship("a", "b", "KNOWS")
    assert "T" in rel["timestamp"]


@pytest.mark.asyncio
async def test_create_relationship_stories_array_in_cypher(goat, mock_graph):
    """stories must be stored as a list, not a plain string."""
    mock_graph.query.return_value = make_result([make_edge({})])
    await goat.create_relationship("a", "b", "KNOWS")
    params = mock_graph.query.call_args[0][1]
    assert params["props"]["stories"] == ["KNOWS"]


@pytest.mark.asyncio
async def test_create_relationship_with_extra_props(goat, mock_graph):
    mock_graph.query.return_value = make_result([make_edge({})])
    rel = await goat.create_relationship("a", "b", "KNOWS", state="pending", weight=5)
    assert rel["state"] == "pending"
    assert rel["weight"] == 5
    params = mock_graph.query.call_args[0][1]
    assert params["props"]["state"] == "pending"
    assert params["props"]["weight"] == 5


@pytest.mark.asyncio
async def test_create_relationship_no_match_returns_none(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    result = await goat.create_relationship("x", "y", "KNOWS")
    assert result is None


@pytest.mark.asyncio
async def test_get_relationships_uses_is_connected_to(goat, mock_graph):
    edge_props = {
        "stories": ["KNOWS"],
        "timestamp": "2026-02-23T10:00:00",
        "relationship_id": "test-uuid",
    }
    mock_graph.query.return_value = make_result(
        ["alice", make_edge(edge_props), "bob"]
    )
    rels = await goat.get_relationships()
    assert len(rels) == 1
    assert rels[0]["story"] == "KNOWS"
    assert rels[0]["source_id"] == "alice"
    assert rels[0]["target_id"] == "bob"
    assert rels[0]["relationship_id"] == "test-uuid"
    cypher = mock_graph.query.call_args[0][0]
    assert "is_connected_to" in cypher


@pytest.mark.asyncio
async def test_get_relationships_story_filter(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    await goat.get_relationships(story="KNOWS")
    cypher = mock_graph.query.call_args[0][0]
    params = mock_graph.query.call_args[0][1]
    assert "$story IN r.stories" in cypher
    assert params["story"] == "KNOWS"


@pytest.mark.asyncio
async def test_get_relationships_source_filter(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    await goat.get_relationships(source="alice")
    cypher = mock_graph.query.call_args[0][0]
    params = mock_graph.query.call_args[0][1]
    assert "n.nodeid = $source" in cypher
    assert params["source"] == "alice"


@pytest.mark.asyncio
async def test_get_relationships_extra_props_returned(goat, mock_graph):
    edge_props = {
        "stories": ["KNOWS"],
        "timestamp": "2026-02-23T10:00:00",
        "relationship_id": "uuid",
        "state": "active",
    }
    mock_graph.query.return_value = make_result(
        ["a", make_edge(edge_props), "b"]
    )
    rels = await goat.get_relationships()
    assert rels[0]["state"] == "active"


@pytest.mark.asyncio
async def test_delete_relationship_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([1])
    assert await goat.delete_relationship("some-uuid") is True
    cypher = mock_graph.query.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "relationship_id" in cypher


@pytest.mark.asyncio
async def test_delete_relationship_not_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([0])
    assert await goat.delete_relationship("no-such-uuid") is False


# ---------------------------------------------------------------------------
# update_relationship_props — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_relationship_props_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([1])
    result = await goat.update_relationship_props("some-uuid", state="confirmed")
    assert result is True
    cypher = mock_graph.query.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "SET r +=" in cypher
    params = mock_graph.query.call_args[0][1]
    assert params["rid"] == "some-uuid"
    assert params["props"]["state"] == "confirmed"


@pytest.mark.asyncio
async def test_update_relationship_props_not_found(goat, mock_graph):
    mock_graph.query.return_value = make_result([0])
    result = await goat.update_relationship_props("no-such-uuid", state="confirmed")
    assert result is False


@pytest.mark.asyncio
async def test_update_relationship_props_empty_result(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    result = await goat.update_relationship_props("uuid", state="x")
    assert result is False


# ---------------------------------------------------------------------------
# is_the_same_as routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_link_is_uses_is_the_same_as(goat, mock_graph):
    mock_graph.query.return_value = make_result()
    await goat.link_is("a", "b")
    cypher = mock_graph.query.call_args[0][0]
    assert "is_the_same_as" in cypher
    assert "MERGE" in cypher


@pytest.mark.asyncio
async def test_create_relationship_never_uses_is_the_same_as(goat, mock_graph):
    mock_graph.query.return_value = make_result([make_edge({})])
    await goat.create_relationship("a", "b", "is_the_same_as")
    cypher = mock_graph.query.call_args[0][0]
    # story value is in params, not in the relationship type
    assert "is_connected_to" in cypher


# ---------------------------------------------------------------------------
# Analytics — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_composition(goat, mock_graph):
    mock_graph.query.return_value = make_result(
        [["Person", "Employee"]],
        [["Person"]],
        [["Company"]],
    )
    comp = await goat.get_composition()
    assert comp["Person"] == 2
    assert comp["Employee"] == 1
    assert comp["Company"] == 1


@pytest.mark.asyncio
async def test_get_taxonomy(goat, mock_graph):
    mock_graph.query.return_value = make_result(
        ["KNOWS", 2],
        ["LIKES", 1],
    )
    tax = await goat.get_taxonomy()
    assert tax["KNOWS"] == 2
    assert tax["LIKES"] == 1
    cypher = mock_graph.query.call_args[0][0]
    assert "UNWIND r.stories" in cypher
    assert "is_connected_to" in cypher


@pytest.mark.asyncio
async def test_dump_all_rels(goat, mock_graph, tmp_path):
    edge_props = {
        "stories": ["KNOWS"],
        "timestamp": "2026-02-23T10:00:00",
        "relationship_id": "uuid",
    }
    mock_graph.query.return_value = make_result(
        ["alice", make_edge(edge_props), "bob"]
    )
    path = str(tmp_path / "dump.txt")
    count = await goat.dump_all_rels(path)
    assert count == 1
    content = open(path).read()
    assert "alice|KNOWS|bob" in content
    assert "2026-02-23T10:00:00" in content


# ---------------------------------------------------------------------------
# Integration tests — require a live FalkorDB at localhost:6379
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_node_round_trip():
    goat = FalkorGoat(host="localhost", port=6379, graph_name="test_mojogoat")
    try:
        node = await goat.add_node("int_alice", name="Alice", labels=["Person"])
        assert node["nodeid"] == "int_alice"

        fetched = await goat.get_node("int_alice")
        assert fetched is not None
        assert fetched["name"] == "Alice"
        assert "Person" in fetched.get("labels", [])
    finally:
        await goat.delete_node("int_alice")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_relationship_round_trip():
    goat = FalkorGoat(host="localhost", port=6379, graph_name="test_mojogoat")
    try:
        await goat.add_node("int_src", labels=["Node"])
        await goat.add_node("int_tgt", labels=["Node"])

        rel = await goat.create_relationship(
            "int_src", "int_tgt", "KNOWS", state="active"
        )
        assert rel is not None
        assert len(rel["relationship_id"]) == 36
        assert "T" in rel["timestamp"]

        rels = await goat.get_relationships(source="int_src")
        assert any(r["story"] == "KNOWS" for r in rels)
        assert any(r.get("state") == "active" for r in rels)

        rid = rel["relationship_id"]
        rels_by_story = await goat.get_relationships(story="KNOWS")
        assert any(r["relationship_id"] == rid for r in rels_by_story)

        assert await goat.delete_relationship(rid) is True
        rels_after = await goat.get_relationships(source="int_src")
        assert not any(r["relationship_id"] == rid for r in rels_after)
    finally:
        await goat.delete_node("int_src")
        await goat.delete_node("int_tgt")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_link_is():
    goat = FalkorGoat(host="localhost", port=6379, graph_name="test_mojogoat")
    try:
        await goat.add_node("int_n1", labels=["Node"])
        await goat.add_node("int_n2", labels=["Node"])
        # Should not raise
        await goat.link_is("int_n1", "int_n2")
    finally:
        await goat.delete_node("int_n1")
        await goat.delete_node("int_n2")
