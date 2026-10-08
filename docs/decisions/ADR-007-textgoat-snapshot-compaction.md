# ADR-007: TextGoat snapshot file lifecycle — no automatic compaction

**Status:** Accepted (compaction deferred)
**Date:** 2026-02-24

---

## Context

TextGoat persists relationships as append-only snapshot files. Every write operation
(`create_relationship`, `update_relationship_props`, `delete_relationship`) creates a new
snapshot file under `{goatpath}/snapshots/` and updates `goatrels.gq` to point to it.
Old snapshots are never deleted.

In a long-running service handling thousands of writes per day, this will accumulate
unbounded snapshot files (one per write). On a goat with 10,000 writes, there are 10,000
snapshot files, 9,999 of which are orphaned.

The read path loads the single file named in `goatrels.gq` — orphaned snapshots are not
read and have no performance impact on reads. The impact is:

1. **Disk usage:** Each snapshot contains the full relationship set, not a delta. A goat
   with 500 relationships written 10,000 times would occupy ~5 GB.
2. **`ls` / directory operations:** Filesystems with many small files in one directory
   degrade at scale (ext4 with `dir_index` handles ~1M entries, but inode pressure is real).

---

## Decision

**Defer automatic compaction.** TextGoat does not implement compaction at this time.

Rationale:

- MojoGOAT's primary use case (Xetrapal) has low write volume (hundreds to low thousands
  of relationships per goat).
- The operational simplicity of append-only snapshots outweighs the risk for this scale.
- Implementing compaction correctly requires handling concurrent write contention and
  deciding on retention policy (keep N snapshots, keep last N days, etc.).

**Manual compaction** is achievable today: delete `{goatpath}/snapshots/` contents except
the current file named in `goatrels.gq`.

---

## Deferred work

When compaction is needed, the recommended approach is:

1. A `TextGoat.compact()` method that:
   - Reads all non-empty lines from the current snapshot
   - Writes them to a new snapshot
   - Updates `goatrels.gq`
   - Deletes all old snapshot files
2. Call `compact()` automatically after N writes (configurable via constructor, default off)
3. Expose `POST /api/active-goat/compact` in the REST API

Until then, operators can run periodic cleanup via:
```bash
CURRENT=$(cat {goatpath}/goatrels.gq)
find {goatpath}/snapshots/ -not -name "$(basename $CURRENT)" -delete
```

---

## Consequences

- **Positive:** No implementation complexity now.
- **Negative:** Operators of high-write goats must manage snapshots manually.
- **Action:** Add a note to the ops runbook when snapshot count exceeds 1,000.
