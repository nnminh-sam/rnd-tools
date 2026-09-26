"""SQLite storage for documents, blocks, chunks and the FTS5 full-text index.

Stdlib only (sqlite3 + json) so hooks and the verifier start instantly.

Tables
  docs         one row per indexed file (doc_id is the stable, human-readable id)
  blocks       exact extracted text per anchor — the ground truth for reads/citations
  chunks       retrieval units (several consecutive blocks), mirrored into chunks_fts
  chunks_fts   FTS5 index (porter stemming + diacritic folding, so "ghế" finds "ghe")
  tables_meta  SQL tables built from the document's tables (data lives in DuckDB)
  vectors      optional embeddings per chunk (semantic search)
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS docs(
  doc_id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, doc_type TEXT NOT NULL, title TEXT,
  sha256 TEXT, mtime REAL, size INTEGER, indexed_at TEXT, n_blocks INTEGER, meta TEXT
);
CREATE TABLE IF NOT EXISTS blocks(
  doc_id TEXT NOT NULL, seq INTEGER NOT NULL, anchor TEXT NOT NULL, kind TEXT, section TEXT,
  text TEXT NOT NULL, meta TEXT, PRIMARY KEY(doc_id, seq)
);
CREATE INDEX IF NOT EXISTS blocks_anchor ON blocks(doc_id, anchor);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY, doc_id TEXT NOT NULL, anchor TEXT NOT NULL,
  first_seq INTEGER, last_seq INTEGER, section TEXT, text TEXT
);
CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  title, section, text, tokenize = "porter unicode61 remove_diacritics 2"
);
CREATE TABLE IF NOT EXISTS tables_meta(
  table_name TEXT PRIMARY KEY, doc_id TEXT NOT NULL, source_name TEXT, source_anchor TEXT,
  columns TEXT, n_rows INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS vectors(chunk_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB);
"""


@dataclass
class Doc:
    doc_id: str
    path: str
    doc_type: str
    title: str
    sha256: str
    mtime: float
    size: int
    indexed_at: str
    n_blocks: int
    meta: dict[str, Any]


@dataclass
class BlockRow:
    doc_id: str
    seq: int
    anchor: str
    kind: str
    section: str
    text: str
    meta: dict[str, Any]


@dataclass
class ChunkSpec:
    first_seq: int
    last_seq: int
    anchor: str
    section: str
    text: str


class RefError(ValueError):
    pass


# doc refs look like  doc-id#anchor  (anchor optional); calc refs look like calc:12
REF_RE = re.compile(r"^(?P<doc>[a-z0-9][a-z0-9._-]*)(?:#(?P<anchor>.+))?$")
_CELL_RANGE = re.compile(
    r"^(?P<sheet>'(?:[^']|'')+'|[^!']+)!\$?(?P<c1>[A-Z]{1,3})\$?(?P<r1>\d+)(?::\$?(?P<c2>[A-Z]{1,3})\$?(?P<r2>\d+))?$"
)
_LINE_RANGE = re.compile(r"^L(\d+)(?:-L(\d+))?$")
_ROW_RANGE = re.compile(r"^R(\d+)(?:-R(\d+))?$")


def parse_ref(ref: str) -> tuple[str, str | None]:
    m = REF_RE.match(ref.strip().lstrip("@"))
    if not m:
        raise RefError(f"Malformed reference '{ref}'. Expected doc-id#anchor, e.g. kickoff-notes#p12")
    return m.group("doc"), m.group("anchor")


class Store:
    def __init__(self, path: Path | str, readonly: bool = False):
        self.path = Path(path)
        if readonly:
            if not self.path.exists():
                raise FileNotFoundError(f"Index not found: {self.path}. Run the index tool first.")
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=10)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.path), timeout=30)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(_SCHEMA)
            self.conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),)
            )
            self.conn.commit()
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ docs
    @staticmethod
    def _doc(row: sqlite3.Row) -> Doc:
        return Doc(
            row["doc_id"],
            row["path"],
            row["doc_type"],
            row["title"] or "",
            row["sha256"] or "",
            row["mtime"] or 0.0,
            row["size"] or 0,
            row["indexed_at"] or "",
            row["n_blocks"] or 0,
            json.loads(row["meta"] or "{}"),
        )

    def all_docs(self) -> list[Doc]:
        return [self._doc(r) for r in self.conn.execute("SELECT * FROM docs ORDER BY path")]

    def doc(self, doc_id: str) -> Doc | None:
        row = self.conn.execute("SELECT * FROM docs WHERE doc_id = ?", (doc_id,)).fetchone()
        return self._doc(row) if row else None

    def doc_by_path(self, path: str) -> Doc | None:
        row = self.conn.execute("SELECT * FROM docs WHERE path = ?", (path,)).fetchone()
        return self._doc(row) if row else None

    def find_doc(self, key: str) -> Doc | None:
        """Accept a doc_id, a workspace-relative path or a bare filename."""
        d = self.doc(key) or self.doc_by_path(key)
        if d:
            return d
        rows = self.conn.execute("SELECT * FROM docs WHERE path LIKE ? ORDER BY length(path)", (f"%/{key}",)).fetchall()
        return self._doc(rows[0]) if len(rows) == 1 else None

    def touch_doc(self, doc_id: str, mtime: float, size: int) -> None:
        self.conn.execute("UPDATE docs SET mtime = ?, size = ? WHERE doc_id = ?", (mtime, size, doc_id))
        self.conn.commit()

    def replace_doc(self, doc: Doc, blocks: list[BlockRow], chunks: list[ChunkSpec]) -> list[int]:
        """Atomically replace everything stored for a document. Returns new chunk ids."""
        cur = self.conn.cursor()
        cur.execute("BEGIN")
        try:
            self._delete_doc_rows(cur, doc.doc_id)
            cur.execute(
                "INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    doc.doc_id,
                    doc.path,
                    doc.doc_type,
                    doc.title,
                    doc.sha256,
                    doc.mtime,
                    doc.size,
                    doc.indexed_at,
                    len(blocks),
                    json.dumps(doc.meta, ensure_ascii=False, default=str),
                ),
            )
            cur.executemany(
                "INSERT INTO blocks VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        doc.doc_id,
                        b.seq,
                        b.anchor,
                        b.kind,
                        b.section,
                        b.text,
                        json.dumps(b.meta, ensure_ascii=False, default=str) if b.meta else None,
                    )
                    for b in blocks
                ],
            )
            ids = []
            for c in chunks:
                cur.execute(
                    "INSERT INTO chunks(doc_id, anchor, first_seq, last_seq, section, text) VALUES (?,?,?,?,?,?)",
                    (doc.doc_id, c.anchor, c.first_seq, c.last_seq, c.section, c.text),
                )
                cid = cur.lastrowid
                ids.append(cid)
                cur.execute(
                    "INSERT INTO chunks_fts(rowid, title, section, text) VALUES (?,?,?,?)",
                    (cid, doc.title, c.section, c.text),
                )
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        return ids

    def delete_doc(self, doc_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute("BEGIN")
        self._delete_doc_rows(cur, doc_id)
        cur.execute("DELETE FROM tables_meta WHERE doc_id = ?", (doc_id,))
        cur.execute("COMMIT")

    @staticmethod
    def _delete_doc_rows(cur: sqlite3.Cursor, doc_id: str) -> None:
        ids = [r[0] for r in cur.execute("SELECT id FROM chunks WHERE doc_id = ?", (doc_id,))]
        cur.executemany("DELETE FROM chunks_fts WHERE rowid = ?", [(i,) for i in ids])
        cur.executemany("DELETE FROM vectors WHERE chunk_id = ?", [(i,) for i in ids])
        cur.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        cur.execute("DELETE FROM blocks WHERE doc_id = ?", (doc_id,))
        cur.execute("DELETE FROM docs WHERE doc_id = ?", (doc_id,))

    # ---------------------------------------------------------------- blocks
    @staticmethod
    def _block(row: sqlite3.Row) -> BlockRow:
        return BlockRow(
            row["doc_id"],
            row["seq"],
            row["anchor"],
            row["kind"] or "",
            row["section"] or "",
            row["text"],
            json.loads(row["meta"]) if row["meta"] else {},
        )

    def blocks(self, doc_id: str, first_seq: int | None = None, last_seq: int | None = None) -> list[BlockRow]:
        sql = "SELECT * FROM blocks WHERE doc_id = ?"
        args: list[Any] = [doc_id]
        if first_seq is not None:
            sql += " AND seq >= ?"
            args.append(first_seq)
        if last_seq is not None:
            sql += " AND seq <= ?"
            args.append(last_seq)
        return [self._block(r) for r in self.conn.execute(sql + " ORDER BY seq", args)]

    def resolve(self, ref: str) -> tuple[Doc, list[BlockRow]]:
        """Resolve 'doc#anchor' to the exact blocks it denotes (see extract/__init__)."""
        doc_key, anchor = parse_ref(ref)
        doc = self.find_doc(doc_key)
        if doc is None:
            raise RefError(f"Unknown document '{doc_key}'. Use the status or search tool to list doc ids.")
        if not anchor:
            return doc, self.blocks(doc.doc_id)
        blocks = self._resolve_anchor(doc, anchor)
        if not blocks:
            raise RefError(f"Anchor '{anchor}' not found in {doc.doc_id} ({doc.path}). Use outline to see anchors.")
        return doc, blocks

    def _resolve_anchor(self, doc: Doc, anchor: str) -> list[BlockRow]:
        q = "SELECT * FROM blocks WHERE doc_id = ? AND (anchor = ? OR anchor LIKE ? ESCAPE '\\') ORDER BY seq"
        like = anchor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + ".%"
        rows = [self._block(r) for r in self.conn.execute(q, (doc.doc_id, anchor, like))]
        if rows:
            return rows
        m = _CELL_RANGE.match(anchor)
        if m:
            sheet = m.group("sheet")
            if sheet.startswith("'"):
                sheet = sheet[1:-1].replace("''", "'")
            r1 = int(m.group("r1"))
            r2 = int(m.group("r2") or r1)
            out = []
            for b in self.blocks(doc.doc_id):
                if b.meta.get("sheet") == sheet and "r" in b.meta and min(r1, r2) <= b.meta["r"] <= max(r1, r2):
                    out.append(b)
            return out
        for rx in (_LINE_RANGE, _ROW_RANGE):
            m = rx.match(anchor)
            if m:
                lo = int(m.group(1))
                hi = int(m.group(2) or lo)
                out = []
                for b in self.blocks(doc.doc_id):
                    span = _span(b.anchor, rx)
                    if span and span[0] <= hi and span[1] >= lo:
                        out.append(b)
                return out
        if "-" in anchor:
            left, right = anchor.split("-", 1)
            lb = self._resolve_anchor(doc, left)
            rb = self._resolve_anchor(doc, right)
            if lb and rb:
                return self.blocks(doc.doc_id, min(lb[0].seq, rb[0].seq), max(lb[-1].seq, rb[-1].seq))
        return []

    # ---------------------------------------------------------------- search
    def fts(self, match: str, limit: int, doc_ids: Iterable[str] | None = None) -> list[sqlite3.Row]:
        sql = (
            "SELECT c.id, c.doc_id, c.anchor, c.section, c.first_seq, c.last_seq, d.path, d.doc_type, d.title, "
            "bm25(chunks_fts, 2.0, 3.0, 1.0) AS score, "
            "snippet(chunks_fts, 2, '«', '»', ' … ', 28) AS snip "
            "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid JOIN docs d ON d.doc_id = c.doc_id "
            "WHERE chunks_fts MATCH ?"
        )
        args: list[Any] = [match]
        ids = list(doc_ids or [])
        if ids:
            sql += f" AND c.doc_id IN ({','.join('?' * len(ids))})"
            args += ids
        sql += " ORDER BY score LIMIT ?"
        args.append(limit)
        return list(self.conn.execute(sql, args))

    def chunk(self, chunk_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT c.*, d.path, d.doc_type, d.title FROM chunks c JOIN docs d ON d.doc_id = c.doc_id WHERE c.id = ?",
            (chunk_id,),
        ).fetchone()

    # ---------------------------------------------------------------- tables
    def set_tables(self, doc_id: str, metas: list[dict[str, Any]]) -> None:
        cur = self.conn.cursor()
        cur.execute("BEGIN")
        cur.execute("DELETE FROM tables_meta WHERE doc_id = ?", (doc_id,))
        cur.executemany(
            "INSERT OR REPLACE INTO tables_meta VALUES (?,?,?,?,?,?,?)",
            [
                (
                    m["table_name"],
                    doc_id,
                    m["source_name"],
                    m["source_anchor"],
                    json.dumps(m["columns"], ensure_ascii=False),
                    m["n_rows"],
                    json.dumps(m.get("notes", []), ensure_ascii=False),
                )
                for m in metas
            ],
        )
        cur.execute("COMMIT")

    def tables(self) -> list[dict[str, Any]]:
        out = []
        for r in self.conn.execute(
            "SELECT t.*, d.path FROM tables_meta t JOIN docs d ON d.doc_id = t.doc_id ORDER BY t.table_name"
        ):
            out.append(
                {
                    "table_name": r["table_name"],
                    "doc_id": r["doc_id"],
                    "path": r["path"],
                    "source_name": r["source_name"],
                    "source_anchor": r["source_anchor"],
                    "columns": json.loads(r["columns"]),
                    "n_rows": r["n_rows"],
                    "notes": json.loads(r["notes"] or "[]"),
                }
            )
        return out

    def table_names(self) -> set[str]:
        return {r[0] for r in self.conn.execute("SELECT table_name FROM tables_meta")}

    def stats(self) -> dict[str, int]:
        def q(sql: str) -> int:
            return self.conn.execute(sql).fetchone()[0]

        return {
            "docs": q("SELECT count(*) FROM docs"),
            "blocks": q("SELECT count(*) FROM blocks"),
            "chunks": q("SELECT count(*) FROM chunks"),
            "tables": q("SELECT count(*) FROM tables_meta"),
            "vectors": q("SELECT count(*) FROM vectors"),
        }


def _span(anchor: str, rx: re.Pattern[str]) -> tuple[int, int] | None:
    """Line/row span of a block anchor such as 'L10-L14' or 'R7'."""
    m = rx.match(anchor)
    if not m:
        return None
    lo = int(m.group(1))
    return lo, int(m.group(2) or lo)
