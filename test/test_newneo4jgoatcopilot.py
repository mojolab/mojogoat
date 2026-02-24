"""Async pytest tests for Neo4jGoat (newneo4jgoatcopilot.py).

Unit tests mock the neo4j driver session — no live Neo4j required.
Integration tests are marked @pytest.mark.integration and skipped by default:
    python3 -m pytest test/ -m "not integration"

Integration tests require a JSON config file at test/testdata/neo4j_test_config.json:
    {"url": "bolt://localhost:7687", "database": "neo4j", "password": "your_password"}
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, call

# Skip the entire module if the neo4j driver is not installed.
# Install with: pip install neo4j  or  uv sync (it's in project.dependencies).
pytest.importorskip("neo4j")
from mojogoat.goatbases.newneo4jgoatcopilot import Neo4jGoat


# ---------------------------------------------------------------------------
# Helpers: mock neo4j result objects
# ---------------------------------------------------------------------------

class MockResult:
    """Mock neo4j AsyncResult supporting both single() and async-for iteration."""

    def __init__(self, *records):
        self._records = list(records)

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for r in self._records:
            yield r

    async def single(self):
        return self._records[0] if self._records else None


def make_record(**fields):
    """Return a mock record that supports record["key"] subscript access."""
    r = MagicMock()
    r.__getitem__ = MagicMock(side_effect=lambda k: fields.get(k))
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """Mock neo4j async session (async context manager with async run())."""
    sess = AsyncMock()
    sess.__aenter__ = AsyncMock(return_value=sess)
    sess.__aexit__ = AsyncMock(return_value=False)
    return sess


@pytest.fixture
def goat(mock_session):
    """Neo4jGoat instance with the driver replaced by a mock — no config file needed."""
    g = Neo4jGoat.__new__(Neo4jGoat)
    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session
    g.driver = mock_driver
    return g


# ---------------------------------------------------------------------------
# Node CRUD — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_node_returns_dict(goat, mock_session):
    mock_session.run.side_effect = [
        MockResult(),   # MATCH existing -> not found
        MockResult(),   # CREATE node
    ]
    node = await goat.add_node("alice", name="Alice", labels=["Person"])
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"
    assert node["labels"] == ["Person"]
    assert "created" in node and "updated" in node


@pytest.mark.asyncio
async def test_add_node_iso8601_timestamps(goat, mock_session):
    mock_session.run.side_effect = [MockResult(), MockResult()]
    node = await goat.add_node("bob")
    assert "T" in node["created"]
    assert "T" in node["updated"]


@pytest.mark.asyncio
async def test_add_node_updates_existing(goat, mock_session):
    existing = make_record(n={"nodeid": "alice"})
    mock_session.run.side_effect = [
        MockResult(existing),   # MATCH existing -> found
        MockResult(),           # SET n += $props
    ]
    node = await goat.add_node("alice", name="Updated")
    assert node["nodeid"] == "alice"
    # Second run() should use SET, not CREATE
    second_cypher = mock_session.run.call_args_list[1][0][0]
    assert "SET n +=" in second_cypher
    assert "CREATE" not in second_cypher


@pytest.mark.asyncio
async def test_get_node_found(goat, mock_session):
    record = make_record(n={"nodeid": "alice", "name": "Alice"}, lbls=["Person"])
    mock_session.run.return_value = MockResult(record)
    node = await goat.get_node("alice")
    assert node is not None
    assert node["nodeid"] == "alice"
    assert node["name"] == "Alice"
    assert "Person" in node["labels"]


@pytest.mark.asyncio
async def test_get_node_not_found(goat, mock_session):
    mock_session.run.return_value = MockResult()
    assert await goat.get_node("ghost") is None


@pytest.mark.asyncio
async def test_get_nodes(goat, mock_session):
    r1 = make_record(n={"nodeid": "a"}, lbls=["X"])
    r2 = make_record(n={"nodeid": "b"}, lbls=["Y"])
    mock_session.run.return_value = MockResult(r1, r2)
    nodes = await goat.get_nodes()
    assert len(nodes) == 2
    assert {n["nodeid"] for n in nodes} == {"a", "b"}


@pytest.mark.asyncio
async def test_get_nodes_by_label(goat, mock_session):
    r = make_record(n={"nodeid": "p1"}, lbls=["Person"])
    mock_session.run.return_value = MockResult(r)
    nodes = await goat.get_nodes_by_label("Person")
    assert len(nodes) == 1
    assert nodes[0]["nodeid"] == "p1"
    cypher = mock_session.run.call_args[0][0]
    assert "Person" in cypher


@pytest.mark.asyncio
async def test_delete_node_found(goat, mock_session):
    record = make_record(cnt=1)
    mock_session.run.return_value = MockResult(record)
    assert await goat.delete_node("alice") is True
    cypher = mock_session.run.call_args[0][0]
    assert "DETACH DELETE" in cypher


@pytest.mark.asyncio
async def test_delete_node_not_found(goat, mock_session):
    record = make_record(cnt=0)
    mock_session.run.return_value = MockResult(record)
    assert await goat.delete_node("ghost") is False


# ---------------------------------------------------------------------------
# Relationship CRUD — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_relationship_uses_is_connected_to(goat, mock_session):
    record = make_record(r={})
    mock_session.run.return_value = MockResult(record)
    rel = await goat.create_relationship("alice", "bob", "KNOWS")
    assert rel is not None
    cypher = mock_session.run.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "CREATE" in cypher


@pytest.mark.asyncio
async def test_create_relationship_uuid_v4(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(r={}))
    rel = await goat.create_relationship("alice", "bob", "KNOWS")
    assert len(rel["relationship_id"]) == 36
    assert rel["relationship_id"].count("-") == 4


@pytest.mark.asyncio
async def test_create_relationship_iso8601_timestamp(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(r={}))
    rel = await goat.create_relationship("alice", "bob", "KNOWS")
    assert "T" in rel["timestamp"]


@pytest.mark.asyncio
async def test_create_relationship_stories_array_in_params(goat, mock_session):
    """story must be stored as stories: [story] array, not a plain string."""
    mock_session.run.return_value = MockResult(make_record(r={}))
    await goat.create_relationship("alice", "bob", "KNOWS")
    kwargs = mock_session.run.call_args[1]
    assert kwargs["props"]["stories"] == ["KNOWS"]


@pytest.mark.asyncio
async def test_create_relationship_with_extra_props(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(r={}))
    rel = await goat.create_relationship("alice", "bob", "KNOWS", state="pending", weight=5)
    assert rel["state"] == "pending"
    assert rel["weight"] == 5
    kwargs = mock_session.run.call_args[1]
    assert kwargs["props"]["state"] == "pending"
    assert kwargs["props"]["weight"] == 5


@pytest.mark.asyncio
async def test_create_relationship_no_match_returns_none(goat, mock_session):
    mock_session.run.return_value = MockResult()
    result = await goat.create_relationship("x", "y", "KNOWS")
    assert result is None


@pytest.mark.asyncio
async def test_get_relationships_uses_is_connected_to(goat, mock_session):
    r = make_record(
        src="alice", tgt="bob",
        stories=["KNOWS"],
        ts="2026-02-23T10:00:00",
        rid="test-uuid",
        props={"stories": ["KNOWS"], "timestamp": "2026-02-23T10:00:00", "relationship_id": "test-uuid"},
    )
    mock_session.run.return_value = MockResult(r)
    rels = await goat.get_relationships()
    assert len(rels) == 1
    assert rels[0]["source_id"] == "alice"
    assert rels[0]["target_id"] == "bob"
    assert rels[0]["story"] == "KNOWS"
    assert rels[0]["relationship_id"] == "test-uuid"
    cypher = mock_session.run.call_args[0][0]
    assert "is_connected_to" in cypher


@pytest.mark.asyncio
async def test_get_relationships_story_filter(goat, mock_session):
    mock_session.run.return_value = MockResult()
    await goat.get_relationships(story="KNOWS")
    cypher = mock_session.run.call_args[0][0]
    kwargs = mock_session.run.call_args[1]
    assert "$story IN r.stories" in cypher
    assert kwargs["story"] == "KNOWS"


@pytest.mark.asyncio
async def test_get_relationships_source_filter(goat, mock_session):
    mock_session.run.return_value = MockResult()
    await goat.get_relationships(source="alice")
    cypher = mock_session.run.call_args[0][0]
    kwargs = mock_session.run.call_args[1]
    assert "n.nodeid = $source" in cypher
    assert kwargs["source"] == "alice"


@pytest.mark.asyncio
async def test_get_relationships_extra_props_returned(goat, mock_session):
    r = make_record(
        src="a", tgt="b",
        stories=["KNOWS"],
        ts="2026-02-23T10:00:00",
        rid="uuid",
        props={"stories": ["KNOWS"], "timestamp": "2026-02-23T10:00:00",
               "relationship_id": "uuid", "state": "active"},
    )
    mock_session.run.return_value = MockResult(r)
    rels = await goat.get_relationships()
    assert rels[0]["state"] == "active"


@pytest.mark.asyncio
async def test_delete_relationship_found(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(cnt=1))
    assert await goat.delete_relationship("some-uuid") is True
    cypher = mock_session.run.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "relationship_id" in cypher


@pytest.mark.asyncio
async def test_delete_relationship_not_found(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(cnt=0))
    assert await goat.delete_relationship("no-such-uuid") is False


# ---------------------------------------------------------------------------
# update_relationship_props — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_relationship_props_found(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(cnt=1))
    result = await goat.update_relationship_props("some-uuid", state="confirmed")
    assert result is True
    cypher = mock_session.run.call_args[0][0]
    assert "is_connected_to" in cypher
    assert "SET r +=" in cypher
    kwargs = mock_session.run.call_args[1]
    assert kwargs["rid"] == "some-uuid"
    assert kwargs["props"]["state"] == "confirmed"


@pytest.mark.asyncio
async def test_update_relationship_props_not_found(goat, mock_session):
    mock_session.run.return_value = MockResult(make_record(cnt=0))
    assert await goat.update_relationship_props("no-such-uuid", state="confirmed") is False


@pytest.mark.asyncio
async def test_update_relationship_props_no_record(goat, mock_session):
    mock_session.run.return_value = MockResult()
    assert await goat.update_relationship_props("uuid", state="x") is False


# ---------------------------------------------------------------------------
# is_the_same_as routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_link_is_uses_is_the_same_as(goat, mock_session):
    mock_session.run.return_value = MockResult()
    await goat.link_is("a", "b")
    cypher = mock_session.run.call_args[0][0]
    assert "is_the_same_as" in cypher
    assert "MERGE" in cypher


@pytest.mark.asyncio
async def test_create_relationship_never_uses_is_the_same_as(goat, mock_session):
    """story value is stored in stories array, never as the Cypher relationship type."""
    mock_session.run.return_value = MockResult(make_record(r={}))
    await goat.create_relationship("a", "b", "is_the_same_as")
    cypher = mock_session.run.call_args[0][0]
    assert "is_connected_to" in cypher


# ---------------------------------------------------------------------------
# Analytics — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_composition(goat, mock_session):
    r1 = make_record(lbls=["Person", "Employee"], cnt=3)
    r2 = make_record(lbls=["Company"], cnt=1)
    mock_session.run.return_value = MockResult(r1, r2)
    comp = await goat.get_composition()
    assert comp["Person"] == 3
    assert comp["Employee"] == 3
    assert comp["Company"] == 1


@pytest.mark.asyncio
async def test_get_taxonomy_uses_unwind(goat, mock_session):
    r1 = make_record(story="KNOWS", cnt=2)
    r2 = make_record(story="LIKES", cnt=1)
    mock_session.run.return_value = MockResult(r1, r2)
    tax = await goat.get_taxonomy()
    assert tax["KNOWS"] == 2
    assert tax["LIKES"] == 1
    cypher = mock_session.run.call_args[0][0]
    assert "UNWIND r.stories" in cypher
    assert "is_connected_to" in cypher


@pytest.mark.asyncio
async def test_dump_all_rels(goat, mock_session, tmp_path):
    r = make_record(
        src="alice", tgt="bob",
        stories=["KNOWS"],
        ts="2026-02-23T10:00:00",
        rid="uuid",
        props={"stories": ["KNOWS"], "timestamp": "2026-02-23T10:00:00", "relationship_id": "uuid"},
    )
    mock_session.run.return_value = MockResult(r)
    path = str(tmp_path / "dump.txt")
    count = await goat.dump_all_rels(path)
    assert count == 1
    content = open(path).read()
    assert "alice|KNOWS|bob" in content
    assert "2026-02-23T10:00:00" in content


# ---------------------------------------------------------------------------
# Integration tests — require a live Neo4j instance
# Config: test/testdata/neo4j_test_config.json
#   {"url": "bolt://localhost:7687", "database": "neo4j", "password": "your_password"}
# ---------------------------------------------------------------------------

NEO4J_TEST_CONFIG = os.path.join(os.path.dirname(__file__), "testdata", "neo4j_test_config.json")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_node_round_trip():
    goat = Neo4jGoat(NEO4J_TEST_CONFIG)
    try:
        node = await goat.add_node("int_alice", name="Alice", labels=["Person"])
        assert node["nodeid"] == "int_alice"

        fetched = await goat.get_node("int_alice")
        assert fetched is not None
        assert fetched["name"] == "Alice"
        assert "Person" in fetched.get("labels", [])
    finally:
        await goat.delete_node("int_alice")
        await goat.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_relationship_round_trip():
    goat = Neo4jGoat(NEO4J_TEST_CONFIG)
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
        assert await goat.delete_relationship(rid) is True
    finally:
        await goat.delete_node("int_src")
        await goat.delete_node("int_tgt")
        await goat.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_link_is():
    goat = Neo4jGoat(NEO4J_TEST_CONFIG)
    try:
        await goat.add_node("int_n1", labels=["Node"])
        await goat.add_node("int_n2", labels=["Node"])
        await goat.link_is("int_n1", "int_n2")
    finally:
        await goat.delete_node("int_n1")
        await goat.delete_node("int_n2")
        await goat.close()
