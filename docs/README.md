# MojoGOAT — documentation

## Contents

| Doc | What it covers |
|---|---|
| [filing-issues.md](filing-issues.md) | How to report issues and the contributor workflow (ADR → Issue → Todo → branch → MR) |
| [decisions/](decisions/) | Architecture Decision Records — this repo's ADR home (`ADR-NNN-*.md`, currently 0001-0014) |
| `tasks/todo.md` | The local work log (Shipped / Upcoming / Known issues) |
| `tasks/lessons.md` | Dated discoveries and gotchas |

## Project conventions

- **Model/source of truth**: quad storage — `source | story | target | timestamp`
  — see `CLAUDE.md` "Quad Model".
- **ADR-first**: any non-obvious design choice gets an ADR in `docs/decisions/`
  before the code that depends on it.
- **Coding-Agent / Model trailers**: every commit carries `Coding-Agent:`
  (`claude|opencode|manual`) and `Model:` trailers, appended by the
  `prepare-commit-msg` hook. Enable it in a clone with
  `git config core.hooksPath .githooks`.
