# Developing RnD

## Set-up

```bash
cd plugins/rnd/engine
```

```bash
uv sync
```

```bash
uv run pytest -q
```

```bash
uv run ruff check src tests tools && uv run ruff format --check src tests tools
```

Or from the repo root: `make test`, `make lint`, `make demo`, `make eval`.

Load your working copy into Claude Code without installing it:

```bash
claude --plugin-dir plugins/rnd
```

`claude --plugin-dir plugins/rnd plugin details rnd` prints the component inventory and the
always-on token cost of skill/agent descriptions — check it when you add or edit them.

## Layout

```
plugins/rnd/
  .claude-plugin/plugin.json   manifest (bump version on release)
  .mcp.json                    uv run --frozen --project engine rnd-mcp
  hooks/hooks.json             exec-form hooks → rnd-hook <event>
  skills/<name>/SKILL.md       user commands; frontmatter pins model / fork agent
  agents/<name>.md             subagents; frontmatter pins model, effort, tools
  engine/
    src/rnd/
      api.py                   service layer used by cli.py and mcp_server.py
      extract/                 one module per format → Extraction(blocks, tables)
      index/                   store.py (SQLite schema), indexer.py, search.py, vectors.py
      data/tables.py           DuckDB loading, run_sql, calcs
      cite.py, verify.py       citation syntax and the verifier
      render/                  model.py (Markdown), word.py, slides.py, pdf.py, sheets.py
      edit.py, capture.py      surgical edits, web capture
      setup.py                 workspace bootstrap, demo copy, doctor
      hooks.py                 hook handlers (keep imports light — tested)
    tests/                     pytest; golden/kestrel.json is generated
    tools/build_demo.py        generates ../demo and tests/golden
  demo/                        generated — do not edit by hand
  evals/                       claude plugin eval suite
```

## Rules of the codebase

1. **The engine stays deterministic.** No model calls, no network except `capture`.
2. **Anchors are a contract.** Extractors, `Store.resolve`, the verifier and renderers all
   depend on them. Changing an anchor format needs a `SCHEMA_VERSION` bump in
   `index/store.py`, a note in CHANGELOG, and tests for old citations if you migrate them.
3. **One service function per operation** in `api.py` (or the module it delegates to).
   `cli.py` and `mcp_server.py` stay thin adapters with identical output.
4. **Token economy is a feature.** Tool output is plain text, refs first, capped
   (`MAX_OUT`). Tool/skill/agent descriptions are paid for in every session — keep them
   short and specific.
5. **Hooks never break a session.** Catch everything, exit 0, write diagnostics to stderr,
   and keep `rnd.hooks` / `rnd.verify` free of heavy imports (`test_hooks_and_verifier_import_light`).
6. **Precision beats convenience.** When unsure, refuse with a clear message (e.g. render
   on failed verification, in-place edits of workbooks with charts) rather than guess.

## Claude Code behaviours the plugin depends on

Each of these cost real money or failed silently in the first live test; the tests in
`engine/tests/test_plugin.py` and `test_mcp.py` guard them.

- **Plugin agents are namespaced.** In a skill's `agent:` field and in the Agent tool's
  `subagent_type`, the librarian is `rnd:librarian`. A bare `librarian` does not match;
  a forked skill then silently runs on `general-purpose` with the *session* model (Opus
  for many users). Forked skills also set `model:` explicitly (it overrides the agent's).
- **A skill's `model:` lasts one turn.** Orchestrating skills must launch agents with
  `run_in_background: false`. Background agents report back in a later turn, which runs
  on the session model — in the first test that was 40% of the bill.
- **Subagents cannot Write report-like names.** Claude Code refuses a subagent's Write to
  any `.md` whose basename matches `^(REPORT|SUMMARY|FINDINGS|ANALYSIS).*\.md$`
  (case-insensitive) with "Subagents should return findings as text". RnD names drafts
  `figures-…`, `brainstorm-…`, `decision-…`, `answer-…`, `<subject>.md`.
- **Agents need absolute paths.** A forked skill's prompt starts with "Base directory for
  this skill: …/skills/<name>", and agents have built paths relative to it. Skills pass
  `${CLAUDE_PROJECT_DIR}/outputs/…` (Claude Code substitutes it); `status` prints the
  write locations; `verify` and the post-write hook refuse files outside the workspace.
- **MCP errors are hidden unless they are `ToolError`.** The MCP SDK replaces any other
  exception with "Error executing tool <name>". `mcp_server._tool` converts engine
  exceptions so the model sees the message.
- **UserPromptSubmit also fires on harness messages** (`<task-notification>` when a
  background agent finishes). The prompt hook ignores prompts starting with `<`.
- **SessionStart sees only the starting model.** A later `/model opus` is detected by the
  prompt hook from the transcript's latest assistant message.
- **Project permissions need trust.** `.claude/settings.json` `permissions.allow` is
  ignored until the folder has been opened interactively and trusted; headless runs
  (`claude -p`) in a new folder need `--allowedTools`.

To see what really ran, summarise a session transcript (main thread plus every subagent,
by agent type and model, at list prices):

```bash
uv run python tools/session_cost.py ~/.claude/projects/<folder>/<session-id>.jsonl
```

A `general-purpose` row means a skill named an agent that does not exist. For exact
totals, run a lesson headless in a copy of the demo — `claude -p "/rnd:ask …" --model opus
--output-format json --allowedTools "mcp__plugin_rnd_rnd__*" Read Write Edit Glob Skill Agent`
— and read `total_cost_usd` and `modelUsage`.

## Common changes

### Support a new file type

1. Add `extract/<format>.py` with `extract(path) -> Extraction`. Choose anchors a person
   can find in the file and document them in `extract/__init__.py`.
2. Register the suffix in `extract/_registry()` and the extension in `DEFAULT_CONFIG`.
3. If blocks need custom grouping, extend `make_chunks` in `index/indexer.py`; if anchors
   have a new shape, extend `Store._resolve_anchor` and `render/model._human_location`.
4. Add a fixture file and tests for extraction, resolution and citation verification.

### Add an MCP tool

1. Implement the operation in the engine (service function returning text).
2. Add a `@mcp.tool()` in `mcp_server.py` (use `annotations=READ_ONLY` when it does not
   write) and the mirror sub-command in `cli.py`.
3. If it is safe to run without asking, add it to `READ_ONLY_TOOLS` in `setup.py`.
4. Add it to the `tools:` list of the agents that should use it.

### Add or change a command (skill) or agent

- Skills: `skills/<name>/SKILL.md`. Use `context: fork` + `agent: rnd:<name>` + `model:`
  for single-agent tasks, or `model: sonnet` for orchestration skills that launch several
  agents with `run_in_background: false`. State the task completely — a forked skill does
  not see the conversation — and give absolute paths (`${CLAUDE_PROJECT_DIR}/…`).
- Agents: `agents/<name>.md` with `model`, `effort`, and an explicit `tools` list (least
  privilege). Plugin agents ignore `permissionMode`, `hooks` and `mcpServers`.
- Run `claude plugin validate plugins/rnd/skills` / `…/agents` and the eval suite.

### Change the demo data

Edit the DATA section of `engine/tools/build_demo.py`, then:

```bash
uv run python tools/build_demo.py
```

This rewrites `demo/kestrel-chair/`, `demo/TUTORIAL.md` and `tests/golden/kestrel.json`
together. Run the tests; fix code, not golden numbers.

## Evals (model-backed regression tests)

`plugins/rnd/evals/` holds `claude plugin eval` cases that seed the KESTREL workspace and
run real commands. They cost real tokens; run them before releases or after changing a
skill, agent or tool description:

```bash
claude plugin eval plugins/rnd --scaffold --mocks off --allow-tools 'mcp__plugin_rnd_rnd__*' Write Edit Agent Skill --runs 1 --tag smoke --max-cost-usd 5
```

- `--scaffold` runs each case's `fixture.sh` (copies the demo and indexes it).
- `--mocks off` starts the real RnD MCP server.
- Drop `--tag smoke` to include the slower `decide` and `report` cases; add
  `--ablation none` to skip the no-plugin baseline arm and halve the cost.
- The eval folder is trusted only after you confirm it once interactively.

## Releasing

1. Bump `version` in `.claude-plugin/plugin.json` and `engine/pyproject.toml`.
2. `uv lock` in `engine/` if dependencies changed (the MCP server runs with `--frozen`).
3. Update CHANGELOG.md; run tests, lint and the smoke evals.
4. Users update with `claude plugin marketplace update rnd-tools` and restart.
