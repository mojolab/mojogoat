# MojoGOAT — documentation

## Contents

| Doc | What it covers |
|---|---|
| [filing-issues.md](filing-issues.md) | How to report issues and the contributor workflow (ADR → Issue → Todo → branch → MR) |
| [adr/](adr/) | Architecture Decision Records — this repo's ADR home (`ADR-NNN-*.md`, currently 0001-0013) |
| `tasks/todo.md` | The local work log (Shipped / Upcoming / Known issues) |
| `tasks/lessons.md` | Dated discoveries and gotchas |

Note: this repo uses `docs/adr/` for decision records (not `docs/decisions/`).
Keep new ADRs there, numbered sequentially.

## Project conventions

- **Model/source of truth**: quad storage — `source | story | target | timestamp`
  — see `CLAUDE.md` "Quad Model".
- **ADR-first**: any non-obvious design choice gets an ADR in `docs/adr/`
  before the code that depends on it.
- **Coding-Agent trailers**: every commit carries a `Coding-Agent:`
  `claude|opencode|manual` trailer, appended by the `prepare-commit-msg` hook.
  Enable it in a clone with `git config core.hooksPath .githooks`.
