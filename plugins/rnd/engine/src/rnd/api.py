"""Service layer: one function per user-facing operation, returning compact text.

Both adapters (cli.py for humans and hooks, mcp_server.py for Claude) call these
functions, so behaviour and output format are identical everywhere. Output is plain
text designed to be cheap in tokens: refs first, no decoration, hard size caps.
"""

from __future__ import annotations

from pathlib import Path

from .index.store import RefError, Store
from .util import human_location, truncate
from .workspace import Workspace

# ------------------------------------------------------------------ status


def pending_changes(ws: Workspace) -> tuple[list[str], list[str], list[str]]:
    """(new, modified, deleted) source files relative to the index."""
    indexed = {}
    if ws.index_path.exists():
        with Store(ws.index_path, readonly=True) as store:
            indexed = {d.path: d for d in store.all_docs()}
    new, modified = [], []
    on_disk = set()
    for p in ws.iter_source_files():
        rel = ws.rel(p)
        on_disk.add(rel)
        d = indexed.get(rel)
        if d is None:
            new.append(rel)
        else:
            st = p.stat()
            if st.st_size != d.size or abs(st.st_mtime - d.mtime) > 1e-6:
                modified.append(rel)
    deleted = sorted(set(indexed) - on_disk)
    return new, modified, deleted


def status(ws: Workspace, list_docs: bool = True) -> str:
    lines = [
        f"Workspace '{ws.name}' at {ws.root}",
        f"Write evidence packs/answers to {ws.packs_dir}/ and drafts to {ws.root / 'outputs'}/ (absolute paths).",
    ]
    if not ws.index_path.exists():
        lines.append("Not indexed yet — run the index tool.")
        return "\n".join(lines)
    new, modified, deleted = pending_changes(ws)
    with Store(ws.index_path, readonly=True) as store:
        st = store.stats()
        docs = store.all_docs()
    lines.append(
        f"Index: {st['docs']} docs, {st['chunks']} chunks, {st['tables']} data tables"
        + (f", {st['vectors']} vectors" if st["vectors"] else "")
        + f". Semantic search: {'on' if ws.config.get('semantic') else 'off'}."
    )
    if new or modified or deleted:
        lines.append(
            f"STALE: {len(new)} new, {len(modified)} modified, {len(deleted)} deleted since last index — run index. "
            + ", ".join((new + modified + deleted)[:10])
        )
    else:
        lines.append("Index is up to date.")
    if list_docs:
        lines.append("\ndoc_id · type · path · title")
        for d in docs:
            warn = " ⚠ " + "; ".join(d.meta.get("warnings", [])) if d.meta.get("warnings") else ""
            lines.append(f"{d.doc_id} · {d.doc_type} · {d.path} · {d.title[:70]}{warn}")
    return "\n".join(lines)


# ------------------------------------------------------------------ read


def read(ws: Workspace, refs: list[str], context: int = 0, max_chars: int = 8000) -> str:
    out: list[str] = []
    with Store(ws.index_path, readonly=True) as store:
        for ref in refs:
            ref = ref.strip().removeprefix("[").removesuffix("]").removeprefix("@").split(" ")[0]
            if ref.startswith("calc:"):
                out.append(_read_calc(ws, ref))
                continue
            try:
                doc, blocks = store.resolve(ref)
            except RefError as exc:
                out.append(f"── {ref}: ERROR {exc}")
                continue
            if context and blocks:
                blocks = store.blocks(doc.doc_id, max(0, blocks[0].seq - context), blocks[-1].seq + context)
            anchor = ref.split("#", 1)[1] if "#" in ref else ""
            where = f" · {human_location(doc.doc_type, anchor)}" if anchor else ""
            out.append(f"── {ref} · {doc.title} ({doc.doc_type}) · {doc.path}{where}")
            section = None
            for b in blocks:
                if b.section and b.section != section and b.kind != "heading":
                    out.append(f"§ {b.section}")
                section = b.section
                prefix = "#" * min(int(b.meta.get("level", 1) or 1), 6) + " " if b.kind == "heading" else ""
                out.append(f"[{b.anchor}] {prefix}{b.text}")
    text, cut = truncate("\n".join(out), max_chars)
    if cut:
        text += f"\n… truncated at {max_chars} chars. Read a narrower anchor (see outline) or raise max_chars."
    return text


def _read_calc(ws: Workspace, ref: str, max_rows: int = 25) -> str:
    """A saved calc as a reader checks it: the SQL, its source files and the exact rows."""
    import json

    from .util import display_number

    path = ws.calcs_dir / f"{ref.split(':', 1)[1]}.json"
    if not path.exists():
        return f"── {ref}: ERROR not found (calcs are created by the sql tool)"
    calc = json.loads(path.read_text())
    lines = [
        f"── {ref} · saved {calc.get('created', '?')} · {calc.get('row_count', len(calc.get('rows', [])))} row(s)"
        f" · from {', '.join(calc.get('source_files', [])) or '-'}",
        "SQL: " + " ".join(calc.get("sql", "").split()),
        "| " + " | ".join(calc.get("columns", [])) + " |",
    ]
    for row in calc.get("rows", [])[:max_rows]:
        lines.append("| " + " | ".join(display_number(v) for v in row) + " |")
    if len(calc.get("rows", [])) > max_rows:
        lines.append(f"… {len(calc['rows']) - max_rows} more rows in {ws.rel(path)}")
    return "\n".join(lines)


# ------------------------------------------------------------------ outline


def outline(ws: Workspace, doc_key: str | None = None, max_items: int = 200) -> str:
    with Store(ws.index_path, readonly=True) as store:
        if not doc_key:
            docs = store.all_docs()
            return "\n".join(
                [f"{len(docs)} documents (pass one doc_id for its outline):"]
                + [f"{d.doc_id} · {d.doc_type} · {d.path} · {d.n_blocks} blocks · {d.title[:60]}" for d in docs]
            )
        doc = store.find_doc(doc_key)
        if doc is None:
            return f"Unknown document '{doc_key}'. Call outline without arguments to list doc ids."
        blocks = store.blocks(doc.doc_id)
        tables = [t for t in store.tables() if t["doc_id"] == doc.doc_id]
    lines = [f"{doc.doc_id} · {doc.title} ({doc.doc_type}) · {doc.path} · {len(blocks)} blocks"]
    items: list[str] = []
    if doc.doc_type in ("docx", "md", "txt", "html"):
        last = None
        n_since = 0
        for b in blocks:
            if b.kind == "heading":
                if last is not None:
                    items[-1] += f"  ({n_since} blocks)"
                lvl = int(b.meta.get("level", 1) or 1)
                items.append(f"{'  ' * max(lvl - 1, 0)}[{b.anchor}] {b.text}")
                last, n_since = b.anchor, 0
            else:
                n_since += 1
                if b.kind == "table_row" and b.anchor.endswith(".r1"):
                    items.append(f"    [{b.anchor.rsplit('.', 1)[0]}] table: {b.text[:100]}")
        if last is not None and items:
            items[-1] += f"  ({n_since} blocks)"
        if not items:
            items = [f"[{b.anchor}] {b.text[:90]}" for b in blocks[:40]]
    elif doc.doc_type == "xlsx":
        items = [f"[{b.anchor}] {b.text}" for b in blocks if b.kind == "sheet"]
    elif doc.doc_type == "pptx":
        for b in blocks:
            if b.kind == "slide":
                items.append(f"[{b.anchor}] {b.section}")
            else:
                items.append(f"    [{b.anchor}] {b.kind}")
    elif doc.doc_type == "pdf":
        for b in blocks:
            first = next((ln for ln in b.text.split("\n") if ln.strip()), "")
            items.append(f"[{b.anchor}] {first[:100]}  ({len(b.text)} chars)")
    else:
        items = [f"[{b.anchor}] {b.text[:100]}" for b in blocks[:20]]
    lines += items[:max_items]
    if len(items) > max_items:
        lines.append(f"… {len(items) - max_items} more")
    if tables:
        lines.append("SQL tables: " + ", ".join(f"{t['table_name']} ({t['n_rows']} rows)" for t in tables))
    warnings = doc.meta.get("warnings") or []
    for w in warnings:
        lines.append(f"warning: {w}")
    return "\n".join(lines)


def resolve_output_path(ws: Workspace, out: str | None, default_name: str, suffix: str) -> Path:
    if out:
        p = ws.abspath(out)
    else:
        p = ws.root / "outputs" / default_name
    if p.suffix.lower() != suffix:
        p = p.with_suffix(suffix)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
