"""Incremental indexer: extract changed files, chunk them, store blocks/chunks, load tables.

A file is re-extracted only when its size/mtime changed *and* its sha256 changed, so
re-running the index on an unchanged workspace costs a directory walk.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..extract import Extraction, doc_type_for, extract
from ..util import now_iso, sha256_file, slugify
from ..workspace import Workspace
from .store import BlockRow, ChunkSpec, Doc, Store


@dataclass
class IndexReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tables: int = 0
    seconds: float = 0.0

    def to_text(self) -> str:
        lines = [
            f"Indexed in {self.seconds:.1f}s: {len(self.added)} added, {len(self.updated)} updated, "
            f"{len(self.removed)} removed, {self.unchanged} unchanged, {len(self.failed)} failed; "
            f"{self.tables} data tables refreshed."
        ]
        for label, items in (("added", self.added), ("updated", self.updated), ("removed", self.removed)):
            if items:
                lines.append(f"{label}: " + ", ".join(items[:30]) + (" …" if len(items) > 30 else ""))
        for path, err in self.failed:
            lines.append(f"FAILED {path}: {err}")
        for w in self.warnings:
            lines.append(f"warning: {w}")
        return "\n".join(lines)


# ----------------------------------------------------------------- chunking


def _merge_anchor(first: str, last: str) -> str:
    if first == last:
        return first
    if "!" in first and "!" in last:  # xlsx rows: Sheet!A5:H5 + Sheet!A9:H9 -> Sheet!A5:H9
        sheet, a = first.rsplit("!", 1)
        _, b = last.rsplit("!", 1)
        return f"{sheet}!{a.split(':')[0]}:{b.split(':')[-1]}"
    if first.startswith("L") and last.startswith("L"):  # md lines: L3-L5 + L20-L22 -> L3-L22
        return f"{first.split('-')[0]}-{last.split('-')[-1]}"
    if first.startswith("R") and last.startswith("R"):
        return f"{first}-{last}"
    return f"{first}-{last}"


def make_chunks(ex: Extraction, blocks: list[BlockRow], chunk_chars: int) -> list[ChunkSpec]:
    """Group consecutive blocks into retrieval chunks that respect document structure."""
    groups: list[list[BlockRow]] = []
    if ex.doc_type == "pptx":
        by_slide: dict[int, list[BlockRow]] = {}
        for b in blocks:
            by_slide.setdefault(b.meta.get("slide", 0), []).append(b)
        groups = list(by_slide.values())
    elif ex.doc_type == "pdf":
        groups = [[b] for b in blocks]
    else:
        cur: list[BlockRow] = []
        size = 0
        for b in blocks:
            boundary = b.kind in ("heading", "sheet") or (cur and cur[-1].meta.get("sheet") != b.meta.get("sheet"))
            if cur and (boundary or size + len(b.text) > chunk_chars):
                groups.append(cur)
                cur, size = [], 0
            cur.append(b)
            size += len(b.text) + 1
            if b.kind == "sheet":  # sheet summary is a chunk of its own
                groups.append(cur)
                cur, size = [], 0
        if cur:
            groups.append(cur)

    chunks = []
    for g in groups:
        if ex.doc_type == "pptx":
            anchor = f"s{g[0].meta.get('slide')}"
        else:
            anchor = _merge_anchor(g[0].anchor, g[-1].anchor)
        chunks.append(ChunkSpec(g[0].seq, g[-1].seq, anchor, g[0].section, "\n".join(b.text for b in g)))
    return chunks


# ----------------------------------------------------------------- doc ids


def _new_doc_id(store: Store, rel_path: str) -> str:
    stem = Path(rel_path).stem
    base = slugify(stem)
    if base.startswith("calc"):
        base = "doc-" + base
    taken = {d.doc_id for d in store.all_docs()}
    if base not in taken:
        return base
    parent = slugify(Path(rel_path).parent.name or "root", max_len=20)
    cand = f"{base}-{parent}"
    n = 2
    while cand in taken:
        cand = f"{base}-{n}"
        n += 1
    return cand


# ----------------------------------------------------------------- main entry


def _extract(ws: Workspace, path: Path, rel: str) -> Extraction:
    if doc_type_for(path) == "xlsx":
        from ..extract import excel

        overrides = {
            key.split("::", 1)[1]: int(v.get("header_row"))
            for key, v in ws.config.get("tables", {}).items()
            if key.split("::", 1)[0] == rel and "::" in key and v.get("header_row")
        }
        return excel.extract(path, header_overrides=overrides)
    return extract(path)


def index_workspace(
    ws: Workspace,
    force: bool = False,
    only: list[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> IndexReport:
    started = time.time()
    report = IndexReport()
    store = Store(ws.index_path)
    try:
        files = ws.iter_source_files()
        if only:
            wanted = {ws.rel(p) for p in only}
            files = [f for f in files if ws.rel(f) in wanted]
        seen: set[str] = set()
        changed: list[tuple[Doc, Extraction]] = []
        for path in files:
            rel = ws.rel(path)
            seen.add(rel)
            st = path.stat()
            existing = store.doc_by_path(rel)
            if existing and not force and existing.size == st.st_size and abs(existing.mtime - st.st_mtime) < 1e-6:
                report.unchanged += 1
                continue
            digest = sha256_file(path)
            if existing and not force and existing.sha256 == digest:
                store.touch_doc(existing.doc_id, st.st_mtime, st.st_size)
                report.unchanged += 1
                continue
            if progress:
                progress(f"extracting {rel}")
            try:
                ex = _extract(ws, path, rel)
            except Exception as exc:  # a broken file must not stop the whole run
                report.failed.append((rel, f"{type(exc).__name__}: {exc}"))
                continue
            doc_id = existing.doc_id if existing else _new_doc_id(store, rel)
            doc = Doc(
                doc_id,
                rel,
                ex.doc_type,
                ex.title,
                digest,
                st.st_mtime,
                st.st_size,
                now_iso(),
                len(ex.blocks),
                {**ex.meta, "warnings": ex.warnings},
            )
            rows = [BlockRow(doc_id, i, b.anchor, b.kind, b.section, b.text, b.meta) for i, b in enumerate(ex.blocks)]
            chunk_specs = make_chunks(ex, rows, int(ws.config.get("chunk_chars", 1800)))
            store.replace_doc(doc, rows, chunk_specs)
            (report.updated if existing else report.added).append(f"{doc_id} ({rel})")
            report.warnings += [f"{rel}: {w}" for w in ex.warnings]
            changed.append((doc, ex))

        if not only:
            for d in store.all_docs():
                if d.path not in seen:
                    store.delete_doc(d.doc_id)
                    report.removed.append(f"{d.doc_id} ({d.path})")

        from ..data import tables as data_tables

        removed_ids = [r.split(" ", 1)[0] for r in report.removed]
        if changed or removed_ids:
            report.tables = data_tables.sync(ws, store, changed, removed_ids)

        if ws.config.get("semantic") and changed:
            from . import vectors

            try:
                vectors.embed_missing(ws, store, progress)
            except ImportError:
                report.warnings.append("semantic search enabled but the 'semantic' extra is not installed")
    finally:
        store.close()
    report.seconds = time.time() - started
    return report


__all__ = ["IndexReport", "index_workspace", "make_chunks"]
