"""Concurrency regression tests for TextGoat and the goat-scoped API (ADR-016).

Context: one Danav per goat, several Danavs running at once against one server. The Flask
server runs every request on its own thread with its own event loop, so TextGoat's write
lock must work across threads (it was an asyncio.Lock, which stalls and loses writes when
waiters and holders sit on different loops).

Each test drives real threads, each with its own event loop, as the server does.
"""
import asyncio
import threading

import pytest

from mojogoat.goatbases.textgoat import TextGoat
from api_support import ApiEnv

WRITERS = 6
PER_WRITER = 10


def _make_goat(tmp_path, name):
    goat = TextGoat({"goatpath": str(tmp_path / name), "goatname": name})

    async def seed():
        for i in range(WRITERS * PER_WRITER + 1):
            await goat.add_node(f"n{i}")

    asyncio.run(seed())
    return goat


def _run_in_threads(targets):
    """Run each callable on its own thread; re-raise the first failure; fail on a hang."""
    errors = []

    def wrap(fn):
        def inner():
            try:
                fn()
            except BaseException as e:  # noqa: BLE001 - surfaced below
                errors.append(e)
        return inner

    threads = [threading.Thread(target=wrap(t), daemon=True) for t in targets]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "writers hung (lost lock wake-up?)"
    if errors:
        raise errors[0]


def _writer(goat, w, results):
    async def go():
        for i in range(PER_WRITER):
            n = w * PER_WRITER + i
            rel = await goat.create_relationship(f"n{n}", f"n{n + 1}", "links to")
            results.append(rel is not None)

    return lambda: asyncio.run(go())


def test_concurrent_writers_on_one_goat_lose_nothing(tmp_path):
    goat = _make_goat(tmp_path, "solo")
    results = []
    _run_in_threads([_writer(goat, w, results) for w in range(WRITERS)])

    assert all(results) and len(results) == WRITERS * PER_WRITER
    assert len(asyncio.run(goat.get_relationships())) == WRITERS * PER_WRITER


def test_two_goats_written_simultaneously_stay_isolated(tmp_path):
    a, b = _make_goat(tmp_path, "danav_a"), _make_goat(tmp_path, "danav_b")
    results = []
    # distinct stories per goat so cross-contamination is detectable
    def tagged(goat, w, story):
        async def go():
            for i in range(PER_WRITER):
                n = w * PER_WRITER + i
                results.append(await goat.create_relationship(f"n{n}", f"n{n + 1}", story) is not None)
        return lambda: asyncio.run(go())

    _run_in_threads(
        [tagged(a, w, "only in a") for w in range(WRITERS)]
        + [tagged(b, w, "only in b") for w in range(WRITERS)]
    )

    assert all(results)
    rels_a = asyncio.run(a.get_relationships())
    rels_b = asyncio.run(b.get_relationships())
    assert len(rels_a) == len(rels_b) == WRITERS * PER_WRITER
    assert {r["story"] for r in rels_a} == {"only in a"}
    assert {r["story"] for r in rels_b} == {"only in b"}


def test_readers_never_see_a_truncated_or_shrinking_graph(tmp_path):
    """A reader (e.g. mojogoat-ui) during writes must never observe fewer relationships than before."""
    goat = _make_goat(tmp_path, "watched")
    stop = threading.Event()
    seen = []

    def reader():
        async def go():
            while not stop.is_set():
                seen.append(len(await goat.get_relationships()))
                await asyncio.sleep(0)
        asyncio.run(go())

    results = []
    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()
    try:
        _run_in_threads([_writer(goat, w, results) for w in range(WRITERS)])
    finally:
        stop.set()
        reader_thread.join(timeout=30)

    assert seen, "reader never ran"
    assert seen == sorted(seen), "a reader saw the graph shrink (torn pointer/snapshot read)"
    assert max(seen) <= WRITERS * PER_WRITER


def test_concurrent_gather_on_one_event_loop_does_not_deadlock(tmp_path):
    """The same-loop case (e.g. a client using asyncio.gather) must not deadlock either."""
    goat = _make_goat(tmp_path, "oneloop")

    async def go():
        return await asyncio.wait_for(
            asyncio.gather(
                *[goat.create_relationship(f"n{i}", f"n{i + 1}", "links to") for i in range(30)]
            ),
            timeout=30,
        )

    assert all(r is not None for r in asyncio.run(go()))
    assert len(asyncio.run(goat.get_relationships())) == 30


def test_compact_during_writes_keeps_every_relationship(tmp_path):
    goat = _make_goat(tmp_path, "compacting")
    results = []

    def compactor():
        async def go():
            for _ in range(5):
                await goat.compact()
                await asyncio.sleep(0)
        asyncio.run(go())

    _run_in_threads([_writer(goat, w, results) for w in range(WRITERS)] + [compactor])

    assert all(results)
    assert len(asyncio.run(goat.get_relationships())) == WRITERS * PER_WRITER


def test_api_two_goats_concurrent_http_writes(tmp_path):
    """End to end through the Flask app: two goats, several simultaneous clients each."""
    env = ApiEnv().start()
    try:
        names = ["danav_a", "danav_b"]
        for name in names:
            env.create_text_goat(name)
            for i in range(WRITERS * PER_WRITER + 1):
                r = env.client.post(f"/api/goats/{name}/nodes", json={"nodeid": f"n{i}"})
                assert r.status_code == 201

        statuses = []

        def writer(name, w):
            def run():
                client = env.client  # Flask's test client is safe to share across threads
                for i in range(PER_WRITER):
                    n = w * PER_WRITER + i
                    r = client.post(
                        f"/api/goats/{name}/relationships",
                        json={"source": f"n{n}", "target": f"n{n + 1}", "story": f"in {name}"},
                    )
                    statuses.append(r.status_code)
            return run

        _run_in_threads([writer(n, w) for n in names for w in range(WRITERS)])

        assert set(statuses) == {201}
        for name in names:
            r = env.client.get(f"/api/goats/{name}/relationships")
            rels = r.get_json()
            assert len(rels) == WRITERS * PER_WRITER
            assert {x["story"] for x in rels} == {f"in {name}"}
    finally:
        env.stop()
