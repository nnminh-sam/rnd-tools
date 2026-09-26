# Contributing

Thanks for helping improve RnD. Start with [docs/DEVELOPING.md](docs/DEVELOPING.md) —
it covers set-up, the codebase rules and how to add file types, tools, commands and agents.

Set up a clone with `make sync` (engine dependencies plus the git hooks below).

Before opening a pull request:

1. `make lint` and `make test` pass.
2. New behaviour has tests; changes to extraction, anchors or the verifier have tests
   against the KESTREL demo.
3. If you changed a skill, agent or tool description, run the smoke evals (`make eval`)
   and check `claude --plugin-dir plugins/rnd plugin details rnd` for the always-on token
   cost.
4. User-visible changes are listed in CHANGELOG.md.

## Commit messages

Run `make hooks` once after cloning (`make sync` does it too). It installs a `commit-msg`
hook that rejects messages breaking these rules, and a template that shows them while you
write the message.

```
<type>(<scope>): <summary>

- <bullet summarising a change>
- <another bullet>
```

- **Header**: `type(scope): summary`, at most 72 characters. The summary starts in lower
  case (acronyms such as `README` or `P2` are fine) and has no full stop.
- **Body**: one blank line after the header, then one or more `- ` bullets. Wrap a long
  bullet by indenting the next line two spaces. No other prose.
- **No `Co-Authored-By:` lines** or other co-author footers.
- Merge commits, `Revert "…"` and `fixup!`/`squash!` commits are not checked.

| Type | Use for |
|---|---|
| `feat` | a new capability: a command, agent, MCP tool, file type, option |
| `fix` | a bug fix shipped with the next normal release |
| `hot-fix` | an urgent fix to a released version that goes out on its own, usually with a patch-version bump |
| `chore` | no behaviour change: docs, tests, refactors, dependency and version bumps, tooling |

The scope names the component you changed. Use several separated by commas
(`feat(skill,agent): …`), and narrow a scope to one item with a slash
(`fix(skill/ask): …`, `feat(extract/pdf): …`).

| Scope | Component |
|---|---|
| `skill` | `plugins/rnd/skills/` — the `/rnd:*` commands |
| `agent` | `plugins/rnd/agents/` |
| `hook` | `plugins/rnd/hooks/` and `engine/src/rnd/hooks.py` |
| `mcp` | `plugins/rnd/.mcp.json` and `engine/src/rnd/mcp_server.py` |
| `engine` | engine changes spanning several modules, `api.py`, `util.py`; `pyproject.toml`, `uv.lock` |
| `extract` | `engine/src/rnd/extract/` — Word, Excel, PowerPoint, PDF, text extraction |
| `index` | `engine/src/rnd/index/` — index, search, vectors |
| `sql` | `engine/src/rnd/data/` — DuckDB tables and calcs |
| `verify` | `engine/src/rnd/verify.py`, `cite.py` — the citation contract |
| `render` | `engine/src/rnd/render/` — docx, pdf, pptx, xlsx output |
| `edit` | `engine/src/rnd/edit.py` |
| `capture` | `engine/src/rnd/capture.py` — web capture |
| `cli` | `engine/src/rnd/cli.py` |
| `setup` | `engine/src/rnd/setup.py`, `workspace.py` — workspace bootstrap and config |
| `demo` | `plugins/rnd/demo/`, `engine/tools/build_demo.py`, the tutorial |
| `eval` | `plugins/rnd/evals/` |
| `test` | `engine/tests/` |
| `docs` | `README.md`, `docs/`, `CONTRIBUTING.md`, `CHANGELOG.md` |
| `plugin` | `plugin.json`, `marketplace.json`, versions and releases |
| `repo` | `Makefile`, `.githooks/`, `.gitmessage`, `.gitignore`, other tooling |

Example:

```
feat(skill): new data crawling skill

- add /rnd:crawl to capture every page under a site section
- index captured pages as soon as they are saved
```

The scope list lives in `.githooks/commit-msg`; a test keeps it and this table in sync.

## Design promises

Keep the two design promises intact: the engine is deterministic and model-free, and
nothing RnD writes for a user reaches an Office file without passing the verifier.
