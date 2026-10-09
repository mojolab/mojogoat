# ADR-008: `delete_relationship` is retained as an administrative capability

**Status:** Accepted
**Date:** 2026-02-24

---

## Context

CLAUDE.md states: *"Never delete relationships — callers manage their own invalidation
via `**props`"*. This was the original design intent: callers set a `state` or similar
property to mark a relationship as inactive/invalid rather than removing the edge.

However, `delete_relationship(relationship_id)` was implemented across all backends
(TextGoat, FalkorGoat, Neo4jGoat, MemoryGoat) and is exposed via
`DELETE /api/relationships/<id>`. This creates a contradiction: the rule says never delete,
but the capability exists.

The original rule was motivated by:
- Immutability: relationship history is preserved
- Safety: accidental deletion is unrecoverable (especially for TextGoat)
- Caller epistemology: MojoGOAT should not interpret what "invalid" means

---

## Decision

**Retain `delete_relationship` in GoatBase and all backends.** Update the rule.

The method serves legitimate use cases that should not be blocked:

1. **Test teardown:** Integration tests need to clean up created relationships.
2. **Administrative correction:** Duplicate relationships created by bugs need to be
   removable without taking the service down.
3. **Data migration:** Moving data between goats requires selective deletion.

The *application-level* rule — that Xetrapal and other callers should never call
`delete_relationship` in normal operation flow — is a caller convention, not a
MojoGOAT contract.

### Revised rule

> **Normal application flow must not call `delete_relationship`.** Use `**props` to
> mark relationships as invalid/superseded (e.g. `smriti_state="invalidated"`).
>
> `delete_relationship` is available for **administrative and testing use only**.
> In the REST API, the `DELETE /api/relationships/<id>` endpoint should not be called
> by application code in production.

---

## Consequences

- **Positive:** Tests can clean up; operators can correct data errors.
- **Positive:** No code needs to be removed or rewritten.
- **Negative:** The capability's existence creates temptation to use it for application
  logic. Code review should catch this.
- **Action:** Update CLAUDE.md to reflect the revised rule.
- **Action:** Add a warning comment to `GoatBase.delete_relationship`.
