"""Helpers shared by every extractor that produces rows (xlsx, csv, docx/pptx/pdf tables)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from ..util import format_value

_NUMERIC_STR = re.compile(r"^[-+]?[$€£¥₫]?\s?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")


def coerce_cell(value: Any) -> Any:
    """Turn numeric-looking strings from Word/PDF tables into numbers for SQL.

    Only unambiguous forms are converted ("1,250", "$349", "12.5"); anything else,
    including percentages and ranges, stays text so no information is invented.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not s:
        return None
    if _NUMERIC_STR.match(s):
        digits = re.sub(r"[^\d.\-+]", "", s)
        try:
            return int(digits) if "." not in digits else float(digits)
        except ValueError:
            return s
    return s


def row_text(header: Sequence[str], values: Sequence[Any], formats: Sequence[str | None] | None = None) -> str:
    """'col: value | col: value' — header names make rows findable by column name."""
    parts = []
    for i, v in enumerate(values):
        shown = (
            format_value(v, formats[i] if formats and i < len(formats) else None)
            if not isinstance(v, str)
            else v.strip()
        )
        if shown == "":
            continue
        name = header[i] if i < len(header) and header[i] else f"col{i + 1}"
        parts.append(f"{name}: {shown}")
    return " | ".join(parts)


def col_letter(idx: int) -> str:
    """1 -> A, 27 -> AA."""
    s = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def sheet_ref(sheet: str) -> str:
    """Excel-style sheet prefix: Results or 'Shell tests' (quoted when needed)."""
    if re.fullmatch(r"[A-Za-z0-9_.]+", sheet):
        return sheet
    return "'" + sheet.replace("'", "''") + "'"
