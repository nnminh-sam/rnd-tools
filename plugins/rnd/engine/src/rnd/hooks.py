"""Claude Code hook handlers (`rnd-hook <event>`, JSON on stdin, JSON on stdout).

Hooks only act inside an RnD workspace, so the plugin is silent in other projects.

  pre-read       PreToolUse(Read): deny reading .docx/.xlsx/.pptx/.pdf directly — it is
                 expensive (whole file into context) and lossy; point to the exact doc id.
  post-write     PostToolUse(Write|Edit): verify Markdown written to outputs/ or .rnd/packs/
                 and send the errors back to Claude so it fixes them before going on.
  session-start  SessionStart: one-paragraph workspace briefing; model coaching on Opus.
  session-index  SessionStart (async): refresh the index in the background.
  prompt         UserPromptSubmit: suggest the matching /rnd:* command for free-form asks
                 (and warn once if the session was switched to Opus mid-way).

Keep this module import-light: it runs on every matching event.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

OFFICE_EXT = {".docx", ".doc", ".xlsx", ".xlsm", ".xls", ".pptx", ".ppt", ".pdf"}
VERIFIED_DIRS = ("outputs/", ".rnd/packs/")
MAX_TIPS_PER_SESSION = 3

ROUTES = [
    (
        re.compile(r"\b(deck|slides?|powerpoint|pptx|presentation)\b", re.IGNORECASE),
        "/rnd:deck <topic>",
        "builds a verified PowerPoint (Haiku finds evidence, Sonnet writes)",
    ),
    (
        re.compile(r"\b(report|memo|write[- ]?up|word doc|docx|summary document)\b", re.IGNORECASE),
        "/rnd:report <topic>",
        "writes a cited, verified Word/PDF report on Sonnet",
    ),
    (
        re.compile(r"\b(decide|decision|should we|go/no-go|trade-?off|recommend)\b", re.IGNORECASE),
        "/rnd:decide <question>",
        "the one command that uses Opus — on a compact, verified evidence pack",
    ),
    (
        re.compile(r"\b(brainstorm|ideas?|ideate|concepts?)\b", re.IGNORECASE),
        "/rnd:brainstorm <topic>",
        "ideas grounded in your data, each labelled evidence vs hypothesis",
    ),
    (
        re.compile(
            r"\b(average|mean|median|sum|total|count|percent|compare|trend|chart|statistic|excel|xlsx|sheet|table)\b",
            re.IGNORECASE,
        ),
        "/rnd:analyze <question>",
        "exact numbers via SQL on Sonnet, citable as calcs",
    ),
    (
        re.compile(r"\b(https?://|website|crawl|scrape|web ?page|online source)\b", re.IGNORECASE),
        "/rnd:capture <url or topic>",
        "saves web sources verbatim so they can be cited",
    ),
    (
        re.compile(r"\b(what|which|who|when|where|why|how|find|summari[sz]e|according)\b", re.IGNORECASE),
        "/rnd:ask <question>",
        "cited answer on Haiku, reading only the relevant snippets instead of whole files",
    ),
]


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj))


def _workspace(start: str | None):
    from .workspace import find_workspace_or_none

    return find_workspace_or_none(start) if start else None


def _doc_id_for(ws, rel: str) -> str | None:
    import sqlite3

    if not ws.index_path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{ws.index_path}?mode=ro", uri=True, timeout=2)
        row = con.execute("SELECT doc_id FROM docs WHERE path = ?", (rel,)).fetchone()
        con.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def pre_read(data: dict) -> None:
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if Path(path).suffix.lower() not in OFFICE_EXT:
        return
    ws = _workspace(str(Path(path).parent) if path else data.get("cwd"))
    if ws is None:
        return
    rel = ws.rel(path)
    doc_id = _doc_id_for(ws, rel)
    tip = (
        f"Use the RnD tools instead: outline(doc='{doc_id}') for its structure, then read(refs=['{doc_id}#<anchor>'])"
        f" for exact text, or search(...) to find passages."
        if doc_id
        else "This file is not indexed yet: call the RnD index tool, then outline/read it by doc id."
    )
    if Path(path).suffix.lower() in (".doc", ".xls", ".ppt"):
        tip = "Legacy binary Office formats are not supported; ask the user to save it as .docx/.xlsx/.pptx."
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"RnD: reading {Path(path).name} with Read loads the whole file and loses "
                f"structure. {tip}",
            }
        }
    )


def post_write(data: dict) -> None:
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path.endswith(".md"):
        return
    ws = _workspace(str(Path(path).parent))
    if ws is None:
        # an agent built the path from the wrong base (e.g. the skill's folder) and wrote
        # outside the workspace it is working for
        home = _workspace(data.get("cwd"))
        if home is not None and Path(path).parent.name in ("outputs", "packs"):
            _emit(
                {
                    "decision": "block",
                    "reason": f"RnD: {Path(path).resolve()} is outside the workspace {home.root}. Write it to "
                    f"{home.root / 'outputs' / Path(path).name} (or {home.packs_dir}/ for packs) and tell the "
                    "user the stray copy can be deleted.",
                }
            )
        return
    rel = ws.rel(path)
    if ".rnd" in rel.split("/")[1:] or (rel.startswith(".rnd/") and not rel.startswith(".rnd/packs/")):
        # e.g. outputs/.rnd/packs/x.md: an agent resolved a relative path from the wrong folder
        _emit(
            {
                "decision": "block",
                "reason": f"RnD: {rel} is in the wrong folder. Evidence packs and answers belong in "
                f"{ws.packs_dir}/{Path(path).name} and drafts in {ws.root / 'outputs'}/ — write the file "
                "there (absolute path) and tell the user the stray copy can be deleted.",
            }
        )
        return
    if not rel.startswith(VERIFIED_DIRS) or not Path(path).exists():
        return
    from .verify import verify_file

    rep = verify_file(ws, path)
    if rep.status == "FAIL":
        _emit({"decision": "block", "reason": "RnD verify found problems in " + rel + ":\n" + rep.to_text(25)})
    else:
        _emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"RnD verify {rep.status}: {rel} — " + rep.to_text(5).split("\n", 1)[1][:600],
                }
            }
        )


def session_start(data: dict) -> None:
    ws = _workspace(data.get("cwd"))
    if ws is None:
        return
    n_docs, stale = 0, 0
    if ws.index_path.exists():
        from .api import pending_changes

        try:
            import sqlite3

            con = sqlite3.connect(f"file:{ws.index_path}?mode=ro", uri=True, timeout=2)
            n_docs = con.execute("SELECT count(*) FROM docs").fetchone()[0]
            con.close()
            new, mod, gone = pending_changes(ws)
            stale = len(new) + len(mod) + len(gone)
        except Exception:
            pass
    ctx = (
        f"RnD workspace '{ws.name}': {n_docs} documents indexed"
        + (f", {stale} changed files being re-indexed in the background" if stale else "")
        + ". Get facts only through the RnD tools (search/read/outline/tables/sql) and cite every claim as "
        "[@doc-id#anchor] or [@calc:N]. Commands: /rnd:ask, /rnd:analyze, /rnd:brainstorm, /rnd:report, "
        "/rnd:deck, /rnd:decide, /rnd:capture, /rnd:show, /rnd:help."
    )
    out: dict = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}
    model = str(data.get("model") or "")
    if "opus" in model.lower():
        out["hookSpecificOutput"]["additionalContext"] += (
            " This session runs on Opus: do not read or search documents yourself — delegate retrieval to the "
            "rnd:librarian agent and numbers to rnd:analyst, then reason over their compact results."
        )
        out["systemMessage"] = (
            "RnD: this session is on Opus. /rnd:* commands already run retrieval on Haiku and "
            "drafting on Sonnet; only /rnd:decide uses Opus. For everyday chat here, "
            "`/model sonnet` halves the per-token price."
        )
    elif not ws.index_path.exists():
        out["systemMessage"] = "RnD: this workspace is not indexed yet — run /rnd:setup."
    _emit(out)


def session_index(data: dict) -> None:
    ws = _workspace(data.get("cwd"))
    if ws is None or not ws.index_path.exists():
        return
    from .api import pending_changes

    new, mod, gone = pending_changes(ws)
    if new or mod or gone:
        from .index.indexer import index_workspace

        index_workspace(ws)


def prompt(data: dict) -> None:
    text = (data.get("prompt") or "").strip()
    # "<task-notification>…" and similar are the harness talking (a background agent
    # finished), not the user: a routing hint there only misleads the model
    if not text or text.startswith(("/", "!", "#", "<")) or len(text) < 12:
        return
    ws = _workspace(data.get("cwd"))
    if ws is None:
        return
    session = data.get("session_id") or ""
    on_opus = "opus" in _session_model(data.get("transcript_path")).lower()
    for rx, command, why in ROUTES:
        if rx.search(text):
            ctx = (
                f"RnD routing hint: this request matches {command.split()[0]} ({why}). "
                "Follow that skill's workflow: use RnD tools and subagents, cite every claim."
            )
            out: dict = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
            if on_opus:
                out["hookSpecificOutput"]["additionalContext"] += (
                    " You are on Opus: delegate retrieval to rnd:librarian and numbers to rnd:analyst "
                    "(run_in_background: false) instead of reading documents yourself."
                )
            if on_opus and _once(ws, session, "opus"):
                out["systemMessage"] = (
                    "RnD: this session is on Opus. /rnd:* commands run their steps on Haiku/Sonnet anyway; "
                    f"free-form questions like this one are answered by Opus. Try `{command}` "
                    "or `/model sonnet` (half the price per token)."
                )
            elif _tip_budget(ws, session):
                out["systemMessage"] = f"Tip: `{command}` {why}."
            _emit(out)
            return


def _session_model(transcript_path: str | None) -> str:
    """Model of the latest main-thread reply (the SessionStart hook cannot see a later /model switch)."""
    if not transcript_path:
        return ""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 256_000))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return ""
    found = re.findall(r'"model"\s*:\s*"(claude-[^"]+)"', tail)
    return found[-1] if found else ""


def _tips_state(ws) -> dict:
    marker = ws.rnd_dir / "tips.json"
    try:
        return json.loads(marker.read_text()) if marker.exists() else {}
    except (OSError, ValueError):
        return {}


def _save_tips(ws, session_id: str, state: dict) -> None:
    keep = {k: v for k, v in state.items() if k.split(":")[0] == session_id}  # only this session's counters
    try:
        (ws.rnd_dir / "tips.json").write_text(json.dumps(keep | {"_ts": time.time()}))
    except OSError:
        pass


def _once(ws, session_id: str, key: str) -> bool:
    state = _tips_state(ws)
    if state.get(f"{session_id}:{key}"):
        return False
    _save_tips(ws, session_id, state | {f"{session_id}:{key}": 1})
    return True


def _tip_budget(ws, session_id: str) -> bool:
    state = _tips_state(ws)
    count = state.get(session_id, 0)
    if count >= MAX_TIPS_PER_SESSION:
        return False
    _save_tips(ws, session_id, state | {session_id: count + 1})
    return True


HANDLERS = {
    "pre-read": pre_read,
    "post-write": post_write,
    "session-start": session_start,
    "session-index": session_index,
    "prompt": prompt,
}


def main() -> None:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    handler = HANDLERS.get(event)
    if handler is None:
        sys.stderr.write(f"usage: rnd-hook {{{'|'.join(HANDLERS)}}}\n")
        raise SystemExit(0)  # never break the session over a hook misconfiguration
    try:
        data = json.loads(sys.stdin.read() or "{}")
        handler(data)
    except Exception as exc:  # a failing hook must not block the user's work
        sys.stderr.write(f"rnd-hook {event}: {type(exc).__name__}: {exc}\n")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
