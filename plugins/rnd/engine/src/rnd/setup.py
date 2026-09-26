"""Workspace bootstrap for Claude Code: project settings, CLAUDE.md, demo copy, doctor.

`claude_setup` is what makes a workspace cheap by default:
  * "model": "sonnet" — the everyday chat model for this folder (users can still /model)
  * read-only RnD tools pre-approved, so agents do not stall on permission prompts
  * a short CLAUDE.md with the grounding rules (loaded into every session and agent)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from .workspace import Workspace

MCP_PREFIX = "mcp__plugin_rnd_rnd__"
READ_ONLY_TOOLS = ["status", "index", "search", "read", "outline", "tables", "sql", "verify", "render", "export_xlsx"]

CLAUDE_MD = """# {name} — RnD workspace

This folder is an RnD research workspace. Sources live in `sources/` and `notes/`; generated work goes to `outputs/`.

Rules for every answer and document produced here:
- Use the RnD tools (search / read / outline / tables / sql) to get facts. Never open .docx/.xlsx/.pptx/.pdf with Read.
- Every factual statement carries a citation: `[@doc-id#anchor]`, or `[@calc:N]` for numbers computed with the sql tool.
- Quote verbatim when quoting: `[@doc-id#anchor "exact words"]`. Do not do arithmetic in your head — use sql.
- Anything not backed by a source must be labelled `Assumption:`, `Hypothesis:` or `Idea:`. If evidence is missing, say so.
- Run verify on any Markdown you write to `outputs/` before rendering it to Word/PowerPoint/PDF.
- Commands: /rnd:ask, /rnd:analyze, /rnd:brainstorm, /rnd:report, /rnd:deck, /rnd:decide, /rnd:capture, /rnd:show, /rnd:help.
- Check any citation with `/rnd:show <ref>`. Never name a draft analysis-*, report-*, summary-* or findings-* (agents cannot write those).
"""


def _merge_settings(path: Path, keep_model: bool) -> list[str]:
    settings = json.loads(path.read_text()) if path.exists() else {}
    changes = []
    if not keep_model and "model" not in settings:
        settings["model"] = "sonnet"
        changes.append('default model for this folder set to "sonnet" (switch any time with /model)')
    perms = settings.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    wanted = [MCP_PREFIX + t for t in READ_ONLY_TOOLS] + [
        "Edit(/outputs/**)",
        "Write(/outputs/**)",
        "Edit(/.rnd/packs/**)",
        "Write(/.rnd/packs/**)",
        "Edit(/notes/**)",
        "Write(/notes/**)",
    ]
    added = [w for w in wanted if w not in allow]
    allow += added
    if added:
        changes.append(
            f"pre-approved {len(added)} RnD read/verify/render tools and writes to outputs/, notes/, .rnd/packs/"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return changes


def claude_setup(ws: Workspace, keep_model: bool = False) -> list[str]:
    changes = _merge_settings(ws.root / ".claude" / "settings.json", keep_model)
    md = ws.root / "CLAUDE.md"
    if not md.exists():
        md.write_text(CLAUDE_MD.format(name=ws.name))
        changes.append("wrote CLAUDE.md with the grounding rules")
    elif "RnD workspace" not in md.read_text():
        with md.open("a") as f:
            f.write("\n" + CLAUDE_MD.format(name=ws.name))
        changes.append("appended RnD grounding rules to CLAUDE.md")
    return changes


def demo_source() -> Path:
    """The bundled KESTREL demo: <plugin>/demo/kestrel-chair."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "demo" / "kestrel-chair"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("Bundled demo workspace not found next to the engine.")


def copy_demo(dest: Path) -> Path:
    src = demo_source()
    dest = dest.resolve()
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} exists and is not empty; choose a new folder.")
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".rnd", "~$*"))
    tutorial = src.parent / "TUTORIAL.md"
    if tutorial.exists():
        shutil.copy2(tutorial, dest / "TUTORIAL.md")
    return dest


def doctor() -> str:
    lines = [f"python {sys.version.split()[0]} at {sys.executable}"]
    for mod in ("docx", "openpyxl", "pptx", "pdfplumber", "duckdb", "markdown_it", "reportlab", "trafilatura", "mcp"):
        try:
            m = __import__(mod)
            lines.append(f"ok   {mod} {getattr(m, '__version__', '')}")
        except Exception as exc:  # pragma: no cover - environment specific
            lines.append(f"FAIL {mod}: {exc}")
    for mod, why in (("fastembed", "semantic search (optional)"), ("matplotlib", "chart images in Word (optional)")):
        try:
            __import__(mod)
            lines.append(f"ok   {mod} — {why}")
        except ImportError:
            lines.append(f"--   {mod} not installed — {why}")
    import sqlite3

    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        lines.append("ok   sqlite fts5")
    except sqlite3.OperationalError:  # pragma: no cover
        lines.append("FAIL sqlite has no FTS5")
    return "\n".join(lines)
