# Repository Guidelines

Project-local instructions for AI agents contributing to om-search.

## Instruction inheritance

This file layers on top of `/home/klarrimore/AGENTS.md` (workstation baseline)
and the parent-chain up to it. Repo-local content wins on conflict.

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`, one file per
ticket. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical role labels, each label string equal to its name. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the repo root is the project glossary, ADRs go
in `docs/adr/`. Read before exploring or editing code. See
`docs/agents/domain.md`.

## Development workflow

- Install uv: `sudo pacman -S --needed uv`
- Provision: `uv sync --extra dev`
- Tests: `uv run pytest`
- Type check: `uv run mypy src/`
- Build: `uv build`
- Install from wheel: `uv tool install dist/*.whl`
- Update manual: `om-search --update`

## Guidelines
- Do not add any Co-Author or nonsense to the commit messages
- This is a **public repository and tool** — no secrets, tokens, API keys, access
  credentials, hardcoded paths to the author's local machine, or internal/
  un-released configuration belongs in any file (code, docs, tests, config
  templates, CI, packaging). Every commit is public. If a value varies per
  machine or deployment, it must be an environment variable, config file
  (gitignored), or install-time default — never hardcoded.
- Do not commit `.env`, scratch files containing real tokens, or debug output
  that leaks system state. Before any write, confirm nothing in the content is
  specific to the author's personal workstation.
