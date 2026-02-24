# ADR-0006: Namespace-scoped short IDs for TextGoat relationship_ids

**Status:** Accepted
**Date:** 2026-02-24
**Supersedes:** ADR-0002 (for the TextGoat backend only)

---

## Context

ADR-0002 established `str(uuid4())` as the `relationship_id` format across all backends.
This was revisited when multi-goat namespacing was introduced: each goat now stores its
data in its own subdirectory (`DEFAULT_DATA_DIR/{goat_name}/`), making it useful for
relationship IDs to carry the namespace they belong to.

Full UUID v4 IDs (`e4665908-bf2f-46af-a048-d176c8aff5fe`) are 36 characters, opaque, and
carry no namespace information. In a multi-goat deployment, a bare UUID cannot be
attributed to a goat without a database lookup.

FalkorGoat and Neo4jGoat store `relationship_id` as a property on a Cypher edge inside a
named graph. The graph name already provides namespace isolation, so changing the ID format
there has no practical benefit and would require changes to Cypher queries and existing
stored data.

---

## Decision

**TextGoat only:** `create_relationship()` generates IDs in the format
`{goatname}:{10_char_base62}`, e.g. `xetrapal:Kj8mNpQr4t`.

- Base-62 alphabet (`[A-Za-z0-9]`), generated with `secrets.choice` (CSPRNG)
- 10 characters → ~59 bits of entropy; collision probability < 1 in 10^12 for 1M relationships
- The goat name prefix makes IDs self-identifying in log files, exports, and cross-goat dumps

**FalkorGoat and Neo4jGoat** continue to use `str(uuid4())` (ADR-0002 unchanged for those
backends).

**MemoryGoat** continues to use `str(uuid4())` — it is a stateless testing/fallback
backend with no persistence and no multi-goat namespacing concern.

### Backward compatibility

`_rel_id_from_line()` in TextGoat reads `parts[4]` as-is. Existing snapshot lines with
UUID-format IDs continue to round-trip correctly. Old format IDs are never rewritten unless
the relationship is updated (at which point the original ID is preserved in `parts[4]`).

---

## Consequences

- **Positive:** Relationship IDs in text dumps and API responses are self-identifying.
- **Positive:** Shorter IDs improve readability in logs and debug output.
- **Negative:** `relationship_id` format now differs between TextGoat and graph backends;
  callers must not assume UUID format.
- **Negative:** ADR-0002's "always UUID v4" invariant is relaxed to "unique string, opaque
  to MojoGOAT, generated at write time". Tests that assert `len(id) == 36` must be updated.
- **Rule:** Never parse or compare the internal structure of a `relationship_id` — treat it
  as an opaque string.
