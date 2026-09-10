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
