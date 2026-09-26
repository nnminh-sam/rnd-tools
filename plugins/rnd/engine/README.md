# rnd engine

Deterministic Python engine behind the RnD Claude Code plugin: extraction, index, search,
DuckDB tables and calcs, citation verification, rendering, edits and web capture.

- Claude uses it through the MCP server (`rnd-mcp`, started by `../.mcp.json`).
- Hooks call `rnd-hook <event>`.
- Humans and scripts use the `rnd` CLI: `uv run rnd --help`.

See [docs/DEVELOPING.md](../../../docs/DEVELOPING.md) for the codebase guide and
[docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) for the design.
