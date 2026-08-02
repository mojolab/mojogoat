# Filing issues

Bugs, feature requests, and questions go to the repository's issue tracker.

## Before you file

1. **Read the docs** — check `docs/` first; most questions are already answered.
2. **Search existing issues** — yours may already be open or closed. Add a
   comment instead of a duplicate.
3. **Reproduce once on a clean state** — rule out stale local state before
   reporting.

## Include this environment information

| Field | Example |
|---|---|
| Project version | tag / commit hash |
| Language / runtime | `python3 --version`, `node --version`, etc. |
| OS / host | macOS / Ubuntu / WSL2 |
| Git | `git --version`; `git config --get core.hooksPath` |
| Command that failed | the exact command line (strip secrets) |

## What to paste — and what never to paste

**Do include:** the exact command, the full error text, and redacted config.

**Never paste:** API keys, credentials, `.env` files, git tokens, session logs
that contain personal prompts or data. Redact before attaching, or describe
instead of pasting.

## Templates

### Bug

```markdown
**Command run**
<exact command>

**Expected**
<what should happen>

**Actual**
<error / description>

**Environment**
- version:
- language/runtime:
- OS:
- git:

**Steps to reproduce**
1. ...
```

### Feature request

```markdown
**What problem does this solve?**

**Proposed behavior**

**Alternatives considered**
```

### Question

Open it with a clear title; tag with `question` if the label exists.

## How work is tracked here

Three layers, each with a distinct job:

1. **Issues** — one issue per *discrete, closable* piece of work (a bug, a
   feature, a single phase step). Issues can be assigned, closed, referenced
   from commits, and grouped.
2. **Milestones** — group issues into a *time-boxed or phased* effort (e.g. a
   rollout). Milestones carry a due date and progress; an issue belongs to at
   most one milestone.
3. **tasks/todo.md** — the local canonical *log* of shipped/upcoming/known
   work, carrying ADR + issue links. The tracker is the issue tracker; the
   record is todo.md.

When to use which:

- **Discrete deliverable** → file an issue.
- **Part of a phase** → file the issue *and* attach it to the matching
  milestone.
- **Time-boxed activity** → milestone + per-step issues, not one big issue.
- **Cross-repo or multi-machine phase** → a project board pulling issues from
  all involved repositories is the best single view; per-repo milestones plus
  one issue per step also works without one.

## Contributing / the workflow used here

1. **ADR first** — for any non-obvious design choice, write a short
   Architecture Decision Record in `docs/decisions/ADR-NNN-<slug>.md` (copy
   `docs/decisions/template.md`; add a row to `docs/decisions/README.md`).
2. **Issue** — open the issue referencing the ADR (or the ADR references the
   issue); attach it to the matching milestone when it is part of a phase.
3. **Todo entry** — add the task to `tasks/todo.md` with a link to the issue.
4. **Branch + PR/MR** — implement on a feature branch (`feat/...`, `fix/...`,
   `docs/...`, `chore/...`) with conventional-commit messages (`feat:`,
   `fix:`, `docs:`, `chore:`). Every commit carries a `Coding-Agent:` trailer
   (see `CLAUDE.md`); enable the hook with:
   ```bash
   git config core.hooksPath .githooks
   ```
5. **Merge via the platform** — then the branch is deleted locally and on the
   remote.

### Repo conventions to respect in a PR

- Follow the language/project conventions in `CLAUDE.md`.
- Run the test suite before pushing (whatever the project defines; see
  `CLAUDE.md`).
- Don't commit secrets; `.env` and credentials are gitignored on purpose.
