# ADR-004: Two Cypher relationship types with a `stories` list property

Date: 2026-02-23
Status: Accepted

## Context

In Cypher (Neo4j, FalkorDB), relationship types are structural — they are part of
the graph schema and cannot be passed as query parameters. A query like
`MATCH (n)-[$story]->(m)` is not valid Cypher.

The MojoGOAT quad model stores `story` as a free-form string supplied by the
caller. If `story` were mapped 1:1 to a Cypher relationship type:

- The graph schema would grow unboundedly with caller-defined story values
- Stories could not be filtered via parameters (`WHERE r.type = $story`)
- Graph indexes on relationship types would be unusable

## Options considered

| Option | Problem |
|---|---|
| Story as relationship type (`[:KNOWS]`) | Unlimited types; not parameterizable |
| Single universal type, `story` as plain property | Simple but loses graph structure |
| Single universal type, `story` in a list property | Allows multi-story edges; parameterizable |
| Two fixed types + `stories` list | Preserves identity semantics; query-friendly |

## Decision

Two Cypher relationship types are used across all graph backends:

- **`is_connected_to`** — all domain relationships. The `story` value is stored
  in a `stories` list property on the edge.
- **`is_the_same_as`** — identity / equivalence pairs only (created via `link_is()`).

Querying by story uses the `IN` operator:
```cypher
MATCH (a)-[r:is_connected_to]->(b) WHERE $story IN r.stories
```

A `stories` list (rather than a `story` scalar) is used so that future edges can
carry multiple story labels without a schema change.

Taxonomy queries use `UNWIND` to count per-story:
```cypher
MATCH ()-[r:is_connected_to]->() UNWIND r.stories AS story RETURN story, count(story)
```

## Consequences

- Graph schema is bounded and predictable regardless of how many story values
  callers introduce.
- Story values are fully parameterizable in Cypher.
- The same model applies to both Neo4jGoat and FalkorGoat — they are
  schema-compatible.
- The `stories` list is an internal Cypher storage detail. The public interface
  (`create_relationship`, `get_relationships`) presents a single `story` string,
  as the quad model requires.
- `is_the_same_as` relationships are not returned by `get_relationships()` and
  are not part of the quad model; they are a graph-layer concern only.
