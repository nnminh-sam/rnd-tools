"""Data layer: every sheet / CSV / document table becomes a DuckDB table.

Numbers in reports should come from SQL, not from a model's arithmetic. Each query
run through `run_sql(save=True)` is stored as a *calc* (.rnd/calcs/<n>.json) holding
the SQL, the full-precision result and the source tables, and can be cited as
[@calc:n]. The verifier checks cited figures against that stored result.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from ..extract import Extraction, Table
from ..index.store import Doc, Store
from ..util import display_number, format_value, now_iso, sql_ident
from ..workspace import Workspace

MAX_SAVED_ROWS = 1000
NULL_TOKENS = {"", "-", "—", "n/a", "na", "n.a.", "none", "null", "tbd", "?"}


class SqlError(RuntimeError):
    pass


def _connect(ws: Workspace, read_only: bool):
    import duckdb

    if read_only and not ws.data_path.exists():
        raise SqlError("No data tables yet. Run the index tool first.")
    last: Exception | None = None
    for _ in range(25):  # another process may hold the write lock briefly
        try:
            con = duckdb.connect(str(ws.data_path), read_only=read_only)
            if read_only:
                # queries may only touch indexed tables, never arbitrary files or the network
                con.execute("SET enable_external_access = false")
            return con
        except duckdb.IOException as exc:
            last = exc
            time.sleep(0.2)
    raise SqlError(f"Data store is busy: {last}")


# ------------------------------------------------------------------ typing


def _infer(values: list[Any]) -> tuple[str, list[Any], list[str]]:
    """Pick a SQL type for a column and convert values. Returns (type, values, notes)."""
    present = [v for v in values if v is not None and not (isinstance(v, str) and v.strip().lower() in NULL_TOKENS)]
    notes: list[str] = []
    tokens = sorted(
        {v.strip() for v in values if isinstance(v, str) and v.strip() and v.strip().lower() in NULL_TOKENS}
    )
    if tokens:
        n = sum(1 for v in values if isinstance(v, str) and v.strip() in tokens)
        notes.append(f"{n} placeholder value(s) {', '.join(repr(t) for t in tokens)} stored as NULL")
    if not present:
        return "VARCHAR", [None] * len(values), notes
    if all(isinstance(v, bool) for v in present):
        return "BOOLEAN", [v if isinstance(v, bool) else None for v in values], notes
    nums = [v for v in present if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(nums) == len(present):
        typ = "BIGINT" if all(isinstance(v, int) for v in nums) else "DOUBLE"
        return typ, [v if isinstance(v, (int, float)) and not isinstance(v, bool) else None for v in values], notes
    if len(nums) >= 0.9 * len(present) and len(present) >= 5:
        odd = sorted({str(v) for v in present if not isinstance(v, (int, float))})
        notes.append(
            f"{len(present) - len(nums)} non-numeric value(s) stored as NULL: {', '.join(repr(o) for o in odd[:5])}"
        )
        return "DOUBLE", [v if isinstance(v, (int, float)) and not isinstance(v, bool) else None for v in values], notes
    if all(isinstance(v, dt.datetime) and v.time() == dt.time(0, 0) for v in present):
        return "DATE", [v.date() if isinstance(v, dt.datetime) else None for v in values], notes
    if all(isinstance(v, dt.datetime) for v in present):
        return "TIMESTAMP", [v if isinstance(v, dt.datetime) else None for v in values], notes
    if all(isinstance(v, (dt.date, dt.datetime)) for v in present):
        return (
            "DATE",
            [(v.date() if isinstance(v, dt.datetime) else v) if isinstance(v, dt.date) else None for v in values],
            notes,
        )
    return "VARCHAR", [None if v is None else format_value(v) for v in values], notes


def _unique(names: list[str]) -> list[str]:
    out: list[str] = []
    for n in names:
        cand, k = n, 2
        while cand in out:
            cand, k = f"{n}_{k}", k + 1
        out.append(cand)
    return out


def table_name(doc_id: str, table: Table) -> str:
    return f"{sql_ident(doc_id)}__{sql_ident(table.name)}"


def _load_table(con, name: str, table: Table) -> dict[str, Any]:
    width = len(table.columns)
    rows = [(list(r) + [None] * width)[:width] for r in table.rows]
    cols = _unique([sql_ident(c) for c in table.columns])
    types, notes = [], list(table.notes)
    converted_cols = []
    for i, col in enumerate(cols):
        typ, vals, col_notes = _infer([r[i] for r in rows])
        types.append(typ)
        converted_cols.append(vals)
        notes += [f"{col}: {n}" for n in col_notes]
    con.execute(f'DROP TABLE IF EXISTS "{name}"')
    con.execute(f'CREATE TABLE "{name}" (' + ", ".join(f'"{c}" {t}' for c, t in zip(cols, types)) + ")")
    data = list(zip(*converted_cols)) if converted_cols else []
    if data:
        con.executemany(f'INSERT INTO "{name}" VALUES (' + ", ".join("?" * width) + ")", data)
    return {
        "table_name": name,
        "source_name": table.name,
        "source_anchor": table.anchor,
        "columns": [{"name": c, "orig": o, "type": t} for c, o, t in zip(cols, table.columns, types)],
        "n_rows": len(rows),
        "notes": notes,
    }


def sync(ws: Workspace, store: Store, changed: list[tuple[Doc, Extraction]], removed_doc_ids: list[str]) -> int:
    """Rebuild the tables of changed documents and drop tables of removed ones."""
    con = _connect(ws, read_only=False)
    count = 0
    try:
        known = {t["table_name"]: t["doc_id"] for t in store.tables()}
        for doc_id in removed_doc_ids:
            for tname, owner in known.items():
                if owner == doc_id:
                    con.execute(f'DROP TABLE IF EXISTS "{tname}"')
        for doc, ex in changed:
            for tname, owner in known.items():
                if owner == doc.doc_id:
                    con.execute(f'DROP TABLE IF EXISTS "{tname}"')
            metas = []
            used: set[str] = set()
            for t in ex.tables:
                name = table_name(doc.doc_id, t)
                while name in used:
                    name += "_x"
                used.add(name)
                metas.append(_load_table(con, name, t))
            store.set_tables(doc.doc_id, metas)
            count += len(metas)
    finally:
        con.close()
    return count


# ------------------------------------------------------------------ queries


@dataclass
class SqlResult:
    sql: str
    columns: list[str]
    rows: list[tuple[Any, ...]]
    row_count: int
    tables: list[str]
    calc_id: int | None = None

    def to_markdown(self, limit: int = 50) -> str:
        if not self.columns:
            return "(no result)"
        head = "| " + " | ".join(self.columns) + " |\n|" + "---|" * len(self.columns)
        body = [
            "| " + " | ".join(display_number(v).replace("|", "\\|") for v in row) + " |" for row in self.rows[:limit]
        ]
        out = head + "\n" + "\n".join(body)
        if self.row_count > limit:
            out += f"\n… {self.row_count - limit} more rows (add LIMIT/aggregation, or export to xlsx)"
        return out


_WRITE_SQL = re.compile(
    r"^\s*(insert|update|delete|create|drop|alter|attach|copy|export|install|load|pragma|set|call)\b", re.IGNORECASE
)


def run_sql(ws: Workspace, sql: str, save: bool = True, max_rows: int = MAX_SAVED_ROWS) -> SqlResult:
    if _WRITE_SQL.match(sql):
        raise SqlError("Only read queries (SELECT / WITH / DESCRIBE / SUMMARIZE) are allowed.")
    import duckdb

    con = _connect(ws, read_only=True)
    try:
        try:
            cur = con.execute(sql)
        except duckdb.Error as exc:
            raise SqlError(_explain_sql_error(ws, str(exc))) from None
        columns = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(max_rows + 1) if columns else []
    finally:
        con.close()
    row_count = len(rows)
    rows = rows[:max_rows]
    with Store(ws.index_path, readonly=True) as store:
        names = store.table_names()
    used = sorted(n for n in names if re.search(rf'(?<![\w"]){re.escape(n)}(?![\w"])|"{re.escape(n)}"', sql))
    res = SqlResult(sql.strip(), columns, [tuple(r) for r in rows], row_count, used)
    if save and columns:
        res.calc_id = save_calc(ws, res)
    return res


def _explain_sql_error(ws: Workspace, msg: str) -> str:
    hint = ""
    if "does not exist" in msg or "not found" in msg.lower():
        hint = "\nHint: call the tables tool to see exact table and column names."
    return msg.split("\n")[0] + hint


# ------------------------------------------------------------------ calcs


def _json_value(v: Any) -> Any:
    if isinstance(v, (dt.date, dt.datetime, dt.time)):
        return v.isoformat()
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    try:
        return float(v)  # Decimal
    except (TypeError, ValueError):
        return str(v)


def save_calc(ws: Workspace, res: SqlResult) -> int:
    ws.calcs_dir.mkdir(parents=True, exist_ok=True)
    existing = [int(p.stem) for p in ws.calcs_dir.glob("*.json") if p.stem.isdigit()]
    calc_id = max(existing, default=0) + 1
    with Store(ws.index_path, readonly=True) as store:
        sources = sorted({t["path"] for t in store.tables() if t["table_name"] in res.tables})
    payload = {
        "id": calc_id,
        "created": now_iso(),
        "sql": res.sql,
        "tables": res.tables,
        "source_files": sources,
        "columns": res.columns,
        "rows": [[_json_value(v) for v in r] for r in res.rows],
        "row_count": res.row_count,
    }
    (ws.calcs_dir / f"{calc_id}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    return calc_id


def load_calc(ws: Workspace, calc_id: int) -> dict[str, Any]:
    path = ws.calcs_dir / f"{calc_id}.json"
    if not path.exists():
        raise SqlError(f"calc:{calc_id} not found in {ws.rel(ws.calcs_dir)}")
    return json.loads(path.read_text())


def list_tables_text(ws: Workspace, pattern: str | None = None) -> str:
    with Store(ws.index_path, readonly=True) as store:
        tables = store.tables()
    if pattern:
        p = pattern.lower()
        tables = [
            t for t in tables if p in t["table_name"] or p in t["path"].lower() or p in (t["source_name"] or "").lower()
        ]
    if not tables:
        return "No data tables" + (f" matching '{pattern}'" if pattern else "") + ". Index Excel/CSV files first."
    lines = [f"{len(tables)} table(s). Query with the sql tool (DuckDB dialect); quote nothing, names are snake_case."]
    for t in tables:
        cols = ", ".join(
            f"{c['name']} {c['type'].lower()}" + (f' ("{c["orig"]}")' if c["orig"] != c["name"] else "")
            for c in t["columns"]
        )
        lines.append(f"\n{t['table_name']}  — {t['n_rows']} rows · from {t['path']} [{t['source_anchor']}]")
        lines.append(f"  columns: {cols}")
        for n in t["notes"]:
            lines.append(f"  note: {n}")
    return "\n".join(lines)
