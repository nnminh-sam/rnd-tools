"""MCP adapter: exposes rnd.api to Claude Code as tools (server name "rnd").

In a plugin the tools are called mcp__plugin_rnd_rnd__<name>. Descriptions are kept
short on purpose: every word here is paid for in every conversation that loads them.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

INSTRUCTIONS = """RnD: exact, cheap access to the research workspace (Word, Excel, PowerPoint, PDF, Markdown).
Workflow: search (several phrasings at once) -> read the refs you need -> cite them as [@ref].
Numbers: tables -> sql (DuckDB); cite results as [@calc:N]. Never compute figures yourself.
Before rendering anything to Office formats, write Markdown to outputs/ and run verify; fix every error.
Never open Office/PDF files with the Read tool: use outline/read here (exact text, far fewer tokens)."""

mcp = MCPServer("rnd", instructions=INSTRUCTIONS)
READ_ONLY = ToolAnnotations(readOnlyHint=True)
_current: dict[str, Path] = {}
MAX_OUT = 24000


def _ws():
    from .workspace import find_workspace

    return find_workspace(_current.get("root"))


def _tool(**kwargs):
    """@mcp.tool() that reports engine errors to the model.

    The MCP SDK hides the message of any exception that is not a ToolError (the model
    only sees "Error executing tool sql"), so an agent could not fix a bad column name
    or learn why render refused. Engine errors are deterministic and safe to show.
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kw):
            try:
                return fn(*args, **kw)
            except ToolError:
                raise
            except (ValueError, KeyError, LookupError, FileNotFoundError, RuntimeError) as exc:
                raise ToolError(str(exc) or type(exc).__name__) from exc
            except Exception as exc:
                raise ToolError(f"{type(exc).__name__}: {exc}") from exc

        return mcp.tool(**kwargs)(wrapper)

    return deco


def _cap(text: str) -> str:
    if len(text) <= MAX_OUT:
        return text
    return text[:MAX_OUT] + f"\n… output truncated at {MAX_OUT} chars; narrow the request."


@_tool()
def setup(path: str = ".", name: str | None = None, keep_model: bool = False, demo: bool = False) -> str:
    """Create (or reopen) an RnD workspace at path, write project settings for Claude Code, and index it.
    demo=True first copies the KESTREL tutorial project into path (which must be new or empty)."""
    from .index.indexer import index_workspace
    from .setup import claude_setup, copy_demo
    from .workspace import find_workspace_or_none, init_workspace

    root = Path(path).expanduser().resolve()
    if demo:
        copy_demo(root)
        name = name or "KESTREL"
    existing = find_workspace_or_none(root)
    ws = existing if existing and existing.root == root else init_workspace(root, name)
    _current["root"] = ws.root
    lines = [f"Workspace '{ws.name}' at {ws.root}"] + ["  " + c for c in claude_setup(ws, keep_model)]
    lines.append(index_workspace(ws).to_text())
    return _cap("\n".join(lines))


@_tool(annotations=READ_ONLY)
def status() -> str:
    """Workspace summary: doc ids, types, titles, stale files, warnings (e.g. scanned PDFs)."""
    from .api import status as _status

    return _cap(_status(_ws()))


@_tool()
def index(force: bool = False) -> str:
    """Index new or changed files (incremental; fast when nothing changed)."""
    from .index.indexer import index_workspace

    return _cap(index_workspace(_ws(), force=force).to_text())


@_tool(annotations=READ_ONLY)
def search(
    queries: list[str],
    k: int = 8,
    mode: Literal["ranked", "exact", "regex"] = "ranked",
    doc_types: list[str] | None = None,
    path_glob: str | None = None,
) -> str:
    """Find evidence. ranked: pass 2-5 phrasings/synonyms of the need, results are fused.
    exact/regex: literal match of queries[0] in every block (codes, numbers, names).
    Returns refs (doc-id#anchor) + snippets; read refs before citing them."""
    from .index.search import exact, format_hits
    from .index.search import search as _search

    ws = _ws()
    if mode != "ranked":
        return _cap(
            exact(ws, queries[0], regex=mode == "regex", k=max(k, 20), doc_types=doc_types, path_glob=path_glob)
        )
    return _cap(format_hits(_search(ws, queries, k=k, doc_types=doc_types, path_glob=path_glob), queries))


@_tool(annotations=READ_ONLY)
def read(refs: list[str], context: int = 0, max_chars: int = 8000) -> str:
    """Exact text of refs such as 'kickoff#p12', 'kickoff#p12-p18', 'deck#s5', 'report#page3',
    "quotes#Quotes!A2:H9", a bare doc id, or 'calc:7' (SQL + rows). context adds N neighbouring blocks."""
    from .api import read as _read

    return _cap(_read(_ws(), refs, context=context, max_chars=max_chars))


@_tool(annotations=READ_ONLY)
def outline(doc: str | None = None) -> str:
    """Structure of one document (headings/sheets/slides/pages with anchors), or all documents."""
    from .api import outline as _outline

    return _cap(_outline(_ws(), doc))


@_tool(annotations=READ_ONLY)
def tables(pattern: str | None = None) -> str:
    """SQL tables built from Excel sheets, CSVs and document tables, with columns and types."""
    from .data.tables import list_tables_text

    return _cap(list_tables_text(_ws(), pattern))


@_tool()
def sql(query: str, save: bool = True, limit: int = 50) -> str:
    """Run a read-only DuckDB query over the workspace tables. Saved results are citable as [@calc:N]."""
    from .data.tables import run_sql

    res = run_sql(_ws(), query, save=save)
    head = f"calc:{res.calc_id} · " if res.calc_id else ""
    return _cap(f"{head}{res.row_count} row(s) · tables: {', '.join(res.tables) or '-'}\n{res.to_markdown(limit)}")


@_tool(annotations=READ_ONLY)
def verify(path: str, show_evidence: bool = False) -> str:
    """Check a Markdown file: refs resolve, quotes are verbatim, every figure matches its cited
    evidence, no uncited figures. show_evidence pairs each claim with its source text."""
    from .verify import verify_file

    rep = verify_file(_ws(), path, collect_evidence=show_evidence)
    return _cap(rep.to_text() + ("\n\n" + rep.evidence_text() if show_evidence else ""))


@_tool()
def render(
    path: str,
    format: Literal["docx", "pdf", "pptx"],
    out: str | None = None,
    template: str | None = None,
    force: bool = False,
) -> str:
    """Render verified Markdown to Word/PDF/PowerPoint in outputs/. Refuses if verify fails
    (force=True stamps the file UNVERIFIED). pptx: '---' separates slides; ```chart blocks use calcs."""
    from .render import render_markdown

    res = render_markdown(_ws(), path, format, out, template, force)
    if not res.ok:
        raise ValueError(res.message)
    return res.message


@_tool()
def export_xlsx(
    calc_ids: list[int],
    out: str | None = None,
    sheet_names: list[str] | None = None,
    chart: Literal["bar", "column", "line", "pie"] | None = None,
) -> str:
    """Write saved calcs to an .xlsx (typed values, native chart, Provenance sheet with SQL)."""
    from .api import resolve_output_path
    from .render.sheets import export_calcs

    ws = _ws()
    return export_calcs(ws, calc_ids, resolve_output_path(ws, out, "figures", ".xlsx"), sheet_names, chart)


@_tool()
def capture(urls: list[str], folder: str = "sources/web", follow_links: int = 0) -> str:
    """Save web pages (main text as Markdown with url/date) or linked PDFs/Office files verbatim
    into the workspace and index them, so they can be quoted and cited. Honours robots.txt."""
    from .capture import capture as _capture
    from .capture import format_results
    from .index.indexer import index_workspace

    ws = _ws()
    res = _capture(ws, urls, folder, follow_links)
    out = format_results(res)
    if any(r.path for r in res):
        out += "\n" + index_workspace(ws, only=[ws.abspath(r.path) for r in res if r.path]).to_text()
    return _cap(out)


@_tool()
def edit_xlsx(
    path: str, cells: dict[str, str | int | float | bool | None], out: str | None = None, in_place: bool = False
) -> str:
    """Set cells in an existing workbook, e.g. {"Quotes!K3": 5.1}. Writes <name>.edited.xlsx
    unless out/in_place (in_place backs up to .rnd/backups)."""
    from .edit import xlsx_set

    return xlsx_set(_ws(), path, cells, out, in_place)


@_tool()
def edit_docx(
    path: str,
    find: str | None = None,
    replace: str | None = None,
    append_markdown: str | None = None,
    out: str | None = None,
    in_place: bool = False,
) -> str:
    """Edit an existing Word file keeping its formatting: find/replace text, or append a Markdown
    section. Writes <name>.edited.docx unless out/in_place."""
    from .edit import docx_append_markdown, docx_replace

    ws = _ws()
    if append_markdown:
        return docx_append_markdown(ws, path, append_markdown, out, in_place)
    if find is None or replace is None:
        raise ValueError("Pass find and replace, or append_markdown.")
    return docx_replace(ws, path, find, replace, out, in_place)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
