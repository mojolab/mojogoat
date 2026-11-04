# Lessons

[2026-02-23] — Used `LINKED_TO` as the Cypher relationship type in Neo4jGoat instead of `is_connected_to` — Rule: always check the Cypher relationship model in CLAUDE.md before writing any Cypher queries.

[2026-02-23] — Implemented `delete_relationship` across all backends before noticing CLAUDE.md says "Never delete relationships" — Rule: read the quad model rules section before implementing CRUD methods.

[2026-11-04] — Guarded the TextGoat relationship read-modify-write with a module-level `asyncio.Lock`; Flask runs each request on its own thread and event loop, so waiters were never woken and concurrent writers on one goat lost writes or timed out (1 of 60 stored) — Rule: any lock shared across requests must be a `threading.Lock` held across code with no `await`; write shared files atomically (temp + `os.replace`); test concurrency with real threads that each own an event loop, and confirm the new test fails on the old code.

[2026-11-04] — Rewrote a CRLF file through a text-mode script and silently converted every line to LF, turning a small fix into a whole-file diff — Rule: check `git ls-files --eol <file>` before scripted edits and preserve the line endings.
