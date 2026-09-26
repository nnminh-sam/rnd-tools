<!--
Title: same format as a commit header — <type>(<scope>): <summary>
e.g. feat(skill): new data crawling skill   (types and scopes: CONTRIBUTING.md)
-->

## Summary

<!-- What this PR does and why, in two to four sentences. Link issues with "Closes #…". -->

## Changes

<!-- One subsection per commit (or per area for a large commit): what changed and why. -->

### <type>(<scope>): <commit summary> (<short sha>)

-

## User impact

<!-- What people using RnD will notice: new or changed commands, behaviour, cost, files
written, anything they must do (update, re-run /rnd:setup). Write "None" for internal
changes. -->

## Release

<!-- Users receive a new copy only when `version` in plugin.json changes. -->

- [ ] Version bumped in `plugins/rnd/.claude-plugin/plugin.json` and `plugins/rnd/engine/pyproject.toml`
- [ ] `uv lock` run in `plugins/rnd/engine`
- [ ] CHANGELOG.md updated
- [ ] No release needed (docs, tests or tooling only)

## How it was tested

- [ ] `make test`
- [ ] `make lint`
- [ ] `make validate`
- [ ] `make eval` — required when a skill, agent or MCP tool description changed
- [ ] Fresh install from GitHub in a throwaway config — for packaging changes (docs/DEVELOPING.md → Releasing)
- [ ] Live run: <!-- command, session model, cost from `claude -p … --output-format json` -->

## Checklist

- [ ] Commits follow the convention in CONTRIBUTING.md (`make hooks` installs the check)
- [ ] The engine stays deterministic and model-free
- [ ] Anchor and citation formats are unchanged, or `SCHEMA_VERSION` is bumped and CHANGELOG says so
- [ ] Nothing reaches an Office file without passing the verifier
- [ ] New behaviour has tests
