# ADR-009: One story per `create_relationship` call; multi-story storage is internal only

**Status:** Accepted
**Date:** 2026-02-24

---

## Context

ADR-004 introduced a `stories` list property on Cypher edges to allow future multi-story
relationships. The property is an array even for single-story relationships:
`stories: ["navigated to"]`.

The interface is `create_relationship(source, target, story: str, **props)` — a single
story string. The multi-story storage capability was never surfaced to callers.

Two problems exist:

1. **Mismatch between storage and interface.** The storage model suggests multi-story
   support, but the public interface never exposes it. Callers cannot create or query
   multi-story relationships.

2. **Read-path truncation.** `_rel_to_quad` in FalkorGoat and Neo4jGoat reads
   `stories[0]` as the single `story` value. If a `stories` array were somehow populated
   with multiple values (e.g. via direct Cypher access), only the first would survive the
   read-path.

---

## Decision

**The public interface remains single-story.** `create_relationship` accepts one `story`
string and always will. The multi-story array is an internal storage artefact for graph
backends only.

Rationale:
- No caller has a use case for multi-story relationships. The stories array was speculative.
- Exposing multi-story creation would complicate filtering (`get_relationships(story=...)`)
  and the quad model (`source|story|target`).
- If multi-story is needed in future, it is a new interface method, not a change to
  `create_relationship`.

The `stories: [story]` array in FalkorGoat/Neo4jGoat storage is retained as-is —
changing it to a scalar would require a data migration. It remains an implementation
detail hidden behind `_rel_to_quad`.

**TextGoat and MemoryGoat** store `story` as a first-class field (not in a list), which
is correct for their flat storage model.

---

## Consequences

- **Positive:** Interface remains simple: one story per relationship.
- **Positive:** The `stories` array causes no harm as long as only `stories[0]` is read.
- **Negative:** The `stories` list property name is misleading for new readers of FalkorGoat
  code. A comment is added to `create_relationship` in graph backends to explain why.
- **Rule:** Never read or query beyond `stories[0]`. Never create a relationship with
  `stories` containing more than one element via the public interface.
