# Repository Guidelines

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, label strings equal to their names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Instruction inheritance

This repo's `AGENTS.md` and `CLAUDE.md` inherit up the folder chain all the way to the home directory. Repo-local instructions layer on top of `/home/klarrimore/AGENTS.md` (workstation baseline) and `/home/klarrimore/CLAUDE.md` (Claude Code extras). Repo files win on conflict with the home-level baseline.
