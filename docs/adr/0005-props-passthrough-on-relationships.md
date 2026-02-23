# ADR-0005: `**props` passthrough on `create_relationship` and `update_relationship_props`

Date: 2026-02-23
Status: Accepted

## Context

Xetrapal's SmritiGraph layer needs to attach domain-specific fields to
relationships — for example `state` (pending / confirmed / rejected),
`confidence`, or `source_uri`. These fields are Xetrapal's concern, not
MojoGOAT's. Encoding them into MojoGOAT's interface (e.g. as named parameters)
would couple the storage engine to a specific caller's domain model.

Previous versions of `create_relationship` had a fixed signature
`(source, target, story)` with no facility for extra data.

## Decision

`create_relationship(source, target, story, **props)` accepts arbitrary keyword
arguments. All extra kwargs are:

- Stored verbatim alongside the core quad fields
- Returned in the response dict
- Preserved on read (`get_relationships`)

A separate method `update_relationship_props(relationship_id, **props)` allows
merging new or updated props into an existing relationship without touching
`source`, `story`, `target`, `timestamp`, or `relationship_id`.

MojoGOAT does not validate, interpret, or constrain the contents of `**props`.

## Consequences

- Xetrapal (and any other caller) can evolve its relationship schema without
  requiring MojoGOAT changes.
- MojoGOAT stays domain-agnostic — it has no knowledge of `state`, `confidence`,
  or any other caller concept.
- All three backends (TextGoat, Neo4jGoat, FalkorGoat) must ensure props survive
  round-trips without loss or transformation.
- No schema validation means invalid or conflicting prop keys are silently stored.
  Validation is the caller's responsibility.
- The `relationship_id`, `timestamp`, `source_id`, `target_id`, and `story` fields
  are protected — `update_relationship_props` cannot overwrite them.
