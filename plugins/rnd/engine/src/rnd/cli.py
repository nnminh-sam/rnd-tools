"""`rnd` command line — the human/dev/hook adapter over rnd.api (same output as the MCP tools)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__


def _ws(args):
    from .workspace import find_workspace

    return find_workspace(args.workspace)


def cmd_init(args) -> str:
    from .index.indexer import index_workspace
    from .setup import claude_setup
    from .workspace import init_workspace

    ws = init_workspace(args.path or ".", args.name, args.semantic)
    lines = [f"Initialised RnD workspace '{ws.name}' at {ws.root}"]
    if not args.no_claude:
        lines += ["  " + c for c in claude_setup(ws, keep_model=args.keep_model)]
    if not args.no_index:
        lines.append(index_workspace(ws).to_text())
    return "\n".join(lines)


def cmd_index(args) -> str:
    from .index.indexer import index_workspace

    ws = _ws(args)
    progress = None if args.quiet else (lambda m: print(m, file=sys.stderr))
    return index_workspace(ws, force=args.force, only=args.files or None, progress=progress).to_text()


def cmd_status(args) -> str:
    from .api import status

    return status(_ws(args), list_docs=not args.brief)


def cmd_search(args) -> str:
    from .index.search import exact, format_hits, search

    ws = _ws(args)
    types = args.type or None
    if args.exact or args.regex:
        return exact(ws, " ".join(args.query), regex=args.regex, k=args.k, doc_types=types, path_glob=args.path)
    queries = args.query if args.multi else [" ".join(args.query)]
    return format_hits(search(ws, queries, k=args.k, doc_types=types, path_glob=args.path), queries)


def cmd_read(args) -> str:
    from .api import read

    return read(_ws(args), args.refs, context=args.context, max_chars=args.max_chars)


def cmd_outline(args) -> str:
    from .api import outline

    return outline(_ws(args), args.doc)


def cmd_tables(args) -> str:
    from .data.tables import list_tables_text

    return list_tables_text(_ws(args), args.pattern)


def cmd_sql(args) -> str:
    from .data.tables import run_sql

    res = run_sql(_ws(args), args.query, save=not args.no_save)
    head = f"calc:{res.calc_id} · " if res.calc_id else ""
    return f"{head}{res.row_count} row(s) · tables: {', '.join(res.tables) or '-'}\n{res.to_markdown(args.limit)}"


def cmd_verify(args) -> str:
    from .verify import verify_file

    rep = verify_file(_ws(args), args.file, collect_evidence=args.evidence)
    if args.json:
        return json.dumps({"status": rep.status, "issues": [i.__dict__ for i in rep.issues]}, indent=1)
    return rep.to_text() + ("\n\n" + rep.evidence_text() if args.evidence else "")


def cmd_render(args) -> str:
    from .render import render_markdown

    res = render_markdown(_ws(args), args.file, args.to, args.out, args.template, args.force)
    if not res.ok:
        raise SystemExit(res.message)
    return res.message


def cmd_export(args) -> str:
    from .api import resolve_output_path
    from .render.sheets import export_calcs

    ws = _ws(args)
    out = resolve_output_path(ws, args.out, "figures", ".xlsx")
    ids = [int(str(c).replace("calc:", "")) for c in args.calcs]
    return export_calcs(ws, ids, out, args.sheets.split(",") if args.sheets else None, args.chart)


def cmd_capture(args) -> str:
    from .capture import capture, format_results
    from .index.indexer import index_workspace

    ws = _ws(args)
    res = capture(ws, args.urls, args.folder, args.follow)
    out = format_results(res)
    if any(r.path for r in res):
        out += "\n" + index_workspace(ws, only=[ws.abspath(r.path) for r in res if r.path]).to_text()
    return out


def cmd_edit(args) -> str:
    from . import edit

    ws = _ws(args)
    if args.kind == "xlsx":
        cells = {}
        for item in args.set or []:
            ref, _, val = item.partition("=")
            cells[ref] = _parse_value(val)
        return edit.xlsx_set(ws, args.file, cells, args.out, args.in_place)
    if args.kind == "docx-replace":
        return edit.docx_replace(ws, args.file, args.find, args.replace, args.out, args.in_place)
    text = Path(args.markdown).read_text(encoding="utf-8")
    return edit.docx_append_markdown(ws, args.file, text, args.out, args.in_place)


def _parse_value(raw: str):
    if raw.startswith("="):
        return raw
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    return raw


def cmd_demo(args) -> str:
    from .setup import copy_demo

    dest = copy_demo(Path(args.dest))
    return f"Demo workspace copied to {dest}. Open Claude Code there and run /rnd:setup, then follow TUTORIAL.md."


def cmd_doctor(args) -> str:
    from .setup import doctor

    return doctor()


def cmd_mcp(args) -> str:
    from .mcp_server import main as mcp_main

    mcp_main()
    return ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rnd", description="RnD engine: precise document search, SQL and verified reports."
    )
    p.add_argument("--version", action="version", version=f"rnd {__version__}")
    p.add_argument("-w", "--workspace", help="workspace folder (default: search upward from cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create a workspace here and index it")
    s.add_argument("path", nargs="?")
    s.add_argument("--name")
    s.add_argument("--semantic", action="store_true", help="enable embeddings (needs the semantic extra)")
    s.add_argument("--no-claude", action="store_true", help="do not write .claude/settings.json and CLAUDE.md")
    s.add_argument("--keep-model", action="store_true", help="do not set the folder's default model to sonnet")
    s.add_argument("--no-index", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("index", help="index new/changed files")
    s.add_argument("files", nargs="*")
    s.add_argument("--force", action="store_true")
    s.add_argument("-q", "--quiet", action="store_true")
    s.set_defaults(fn=cmd_index)

    s = sub.add_parser("status", help="workspace and index status")
    s.add_argument("--brief", action="store_true")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("search", help="ranked or exact search")
    s.add_argument("query", nargs="+")
    s.add_argument("-k", type=int, default=8)
    s.add_argument("--multi", action="store_true", help="treat each argument as a separate query (fused)")
    s.add_argument("--type", action="append", help="docx|xlsx|pptx|pdf|md|csv (repeatable)")
    s.add_argument("--path", help="glob on workspace-relative path, e.g. 'sources/engineering/*'")
    s.add_argument("--exact", action="store_true", help="case-insensitive substring search")
    s.add_argument("--regex", action="store_true")
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("read", help="exact text of refs (doc-id#anchor)")
    s.add_argument("refs", nargs="+")
    s.add_argument("--context", type=int, default=0)
    s.add_argument("--max-chars", type=int, default=8000)
    s.set_defaults(fn=cmd_read)

    s = sub.add_parser("outline", help="structure of a document (anchors)")
    s.add_argument("doc", nargs="?")
    s.set_defaults(fn=cmd_outline)

    s = sub.add_parser("tables", help="list SQL tables built from sheets and document tables")
    s.add_argument("pattern", nargs="?")
    s.set_defaults(fn=cmd_tables)

    s = sub.add_parser("sql", help="run a read-only DuckDB query; saves a citable calc")
    s.add_argument("query")
    s.add_argument("--no-save", action="store_true")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(fn=cmd_sql)

    s = sub.add_parser("verify", help="check citations, quotes and figures in a Markdown file")
    s.add_argument("file")
    s.add_argument("--evidence", action="store_true", help="also print each claim with its evidence")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("render", help="verified Markdown -> docx | pdf | pptx")
    s.add_argument("file")
    s.add_argument("--to", required=True, choices=["docx", "pdf", "pptx"])
    s.add_argument("--out")
    s.add_argument("--template")
    s.add_argument("--force", action="store_true", help="render even if verification fails (stamped UNVERIFIED)")
    s.set_defaults(fn=cmd_render)

    s = sub.add_parser("export", help="saved calcs -> xlsx with provenance")
    s.add_argument("calcs", nargs="+", help="calc ids, e.g. 3 7 or calc:3")
    s.add_argument("--out")
    s.add_argument("--sheets", help="comma-separated sheet names")
    s.add_argument("--chart", choices=["bar", "column", "line", "pie"])
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("capture", help="save web pages/files verbatim into sources/web and index them")
    s.add_argument("urls", nargs="+")
    s.add_argument("--folder", default="sources/web")
    s.add_argument("--follow", type=int, default=0, help="also capture up to N same-site links")
    s.set_defaults(fn=cmd_capture)

    s = sub.add_parser("edit", help="surgical edits of existing Office files (writes a new file by default)")
    s.add_argument("kind", choices=["xlsx", "docx-replace", "docx-append"])
    s.add_argument("file")
    s.add_argument("--set", action="append", help="xlsx: Sheet!B4=value (repeatable)")
    s.add_argument("--find")
    s.add_argument("--replace")
    s.add_argument("--markdown", help="docx-append: Markdown file to append")
    s.add_argument("--out")
    s.add_argument("--in-place", action="store_true", help="overwrite (a backup goes to .rnd/backups)")
    s.set_defaults(fn=cmd_edit)

    s = sub.add_parser("demo", help="copy the KESTREL demo workspace to DEST")
    s.add_argument("dest")
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser("doctor", help="check the environment")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("mcp", help="run the MCP server on stdio")
    s.set_defaults(fn=cmd_mcp)
    return p


def main(argv: list[str] | None = None) -> None:
    from .data.tables import SqlError
    from .edit import EditError
    from .index.store import RefError
    from .workspace import WorkspaceError

    args = build_parser().parse_args(argv)
    try:
        out = args.fn(args)
    except (WorkspaceError, SqlError, RefError, EditError, FileNotFoundError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if out:
        print(out)


if __name__ == "__main__":
    main()
