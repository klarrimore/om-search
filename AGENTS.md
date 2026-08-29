# Repository Guidelines

Project-local instructions for AI agents contributing to om-search.

## Instruction inheritance

This file layers on top of `/home/klarrimore/AGENTS.md` (workstation baseline)
and the parent-chain up to it. Repo-local content wins on conflict.

## Domain context

**CONTEXT.md** at the repo root defines the project glossary. Read it before
exploring or editing code. See `docs/agents/domain.md` for how skills consume
domain docs.

## Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See
`docs/agents/issue-tracker.md`.

## Triage labels

Five canonical role labels defined in `docs/agents/triage-labels.md`.

## Development workflow

- Provision: `uv sync --extra dev`
- Tests: `uv run pytest`
- Type check: `uv run mypy src/`
- Build: `uv build`
- Install from wheel: `uv tool install dist/*.whl`
- Update manual: `om-search --update`

## Guidelines
- Do not add any Co-Author or nonsense to the commit messages
