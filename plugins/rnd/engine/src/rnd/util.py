"""Small shared helpers: slugs, value formatting and number parsing.

Number parsing lives here because the extractor (formatting), the SQL layer (display)
and the citation verifier (matching) must agree on exactly one definition.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import math
import re
import unicodedata
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def slugify(text: str, sep: str = "-", max_len: int = 48) -> str:
    """ASCII slug: 'Customer Interviews (Q2) 2026.docx' -> 'customer-interviews-q2-2026-docx'."""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.replace("đ", "d").replace("Đ", "D")
    ascii_ = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", sep, ascii_).strip(sep)
    return (slug[:max_len].rstrip(sep)) or "x"


def sql_ident(text: str) -> str:
    """Safe, lower-case SQL identifier (snake_case, never starting with a digit)."""
    ident = slugify(text, sep="_", max_len=60)
    if ident[0].isdigit():
        ident = "c_" + ident
    return ident


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def format_value(value: Any, number_format: str | None = None) -> str:
    """Render a cell value as text without losing precision.

    Floats use the shortest repr that round-trips, so '0.1' stays '0.1' and never
    '0.1000000000000000055'. Percent-formatted cells are shown as percentages because
    that is what the human author saw in Excel.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, _dt.datetime):
        if value.time() == _dt.time(0, 0):
            return value.date().isoformat()
        return value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, (_dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        if number_format and "%" in number_format:
            return _plain_number(value * 100) + "%"
        return _plain_number(value)
    if isinstance(value, int):
        if number_format and "%" in number_format:
            return _plain_number(value * 100) + "%"
        return str(value)
    return str(value).strip()


def _plain_number(x: float) -> str:
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    text = repr(round(x, 10))
    if "e" in text or "E" in text:
        text = format(Decimal(text), "f")
    return text


def display_number(x: Any) -> str:
    """Human-friendly rendering for query results (full precision is kept elsewhere)."""
    if isinstance(x, float) and not (math.isnan(x) or math.isinf(x)):
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
        if abs(x) >= 1:
            return f"{x:.4f}".rstrip("0").rstrip(".")
        return f"{x:.6g}"
    if isinstance(x, Decimal):
        return display_number(float(x))
    return format_value(x)


# ---------------------------------------------------------------------------
# Numbers in prose. Used by the verifier to check that every figure in a claim
# is backed by the cited evidence.
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(
    r"(?<![\w.\-/])"  # not glued to a word, part number (KS-204) or path
    r"(?P<cur>[$€£¥₫])?\s?"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s?(?P<suf>%|k\b|K\b|M\b|m\b(?!m)|bn\b|B\b)?"
    r"(?![\w])"
)

_SUFFIX = {"k": 1e3, "K": 1e3, "M": 1e6, "m": 1e6, "bn": 1e9, "B": 1e9}
_APPROX_BEFORE = re.compile(
    r"(about|approx\.?|approximately|around|roughly|nearly|almost|circa|ca\.|~|≈|some|khoảng|gần|xấp xỉ)\s*[$€£¥₫]?\s*$",
    re.IGNORECASE,
)


class Num:
    """A number as written: value plus the precision it was written with."""

    __slots__ = ("approx", "decimals", "end", "is_percent", "start", "text", "trailing_zeros", "value")

    def __init__(
        self,
        text: str,
        value: float,
        decimals: int,
        is_percent: bool,
        trailing_zeros: int,
        start: int = 0,
        approx: bool = False,
    ):
        self.start = start
        self.end = start + len(text)
        self.approx = approx  # written as a rounded figure ("about 150,000", "148k")
        self.text = text
        self.value = value
        self.decimals = decimals
        self.is_percent = is_percent
        self.trailing_zeros = trailing_zeros

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Num({self.text!r})"


def find_numbers(text: str) -> list[Num]:
    out: list[Num] = []
    for m in _NUM_RE.finditer(text):
        raw = m.group("num").replace(",", "")
        suf = m.group("suf") or ""
        try:
            val = float(Decimal(raw))
        except InvalidOperation:  # pragma: no cover - regex guarantees digits
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        int_part = raw.split(".")[0]
        trailing = 0 if decimals else len(int_part) - len(int_part.rstrip("0"))
        approx = bool(_APPROX_BEFORE.search(text[max(0, m.start() - 24) : m.start()]))
        if suf in _SUFFIX:
            mult = _SUFFIX[suf]
            val *= mult
            # "148k" is written to the nearest thousand (or finer if decimals given)
            trailing = max(0, int(math.log10(mult)) - decimals)
            decimals = 0
            approx = True
        out.append(Num(m.group(0).strip(), val, decimals, suf == "%", trailing, m.start(), approx))
    return out


def numbers_match(claim: Num, evidence_values: Iterable[float]) -> bool:
    """True if the claimed figure equals an evidence value at the claim's precision.

    '148,233' matches 148233.33; '148k' and 'about 148,000' match 148233.33 (rounded to
    the thousand) but a bare '148,000' does not; '45%' matches 45 or 0.45.
    """
    # (value, decimals, trailing zeros) readings of the claim
    # coarse rounding (150,000 for 148,250) is accepted only when the text says so
    readings = [(claim.value, claim.decimals, claim.trailing_zeros if claim.approx else 0)]
    if claim.is_percent:
        readings.append((claim.value / 100.0, claim.decimals + 2, 0))
    for ev in evidence_values:
        for value, decimals, trailing in readings:
            if _eq_at_precision(value, ev, decimals, trailing):
                return True
    return False


def _eq_at_precision(claimed: float, ev: float, decimals: int, trailing_zeros: int) -> bool:
    if math.isclose(claimed, ev, rel_tol=1e-9, abs_tol=1e-12):
        return True
    q = 10.0 ** (-decimals)
    if abs(_round_half_up(ev, decimals) - claimed) < q / 1000:
        return True
    if trailing_zeros:
        # a round figure like 150,000 may be a rounding of 148,233 only to its own
        # magnitude: allow rounding to 10^trailing_zeros, never coarser.
        step = 10.0**trailing_zeros
        if abs(round(ev / step) * step - claimed) < 1e-9:
            return True
    return False


def _round_half_up(x: float, decimals: int) -> float:
    d = Decimal(repr(x)).quantize(Decimal(1).scaleb(-decimals), rounding="ROUND_HALF_UP")
    return float(d)


def evidence_numbers(text: str) -> list[float]:
    """Every figure a source states: digits, spelled-out numbers ("Seven tests passed")
    and dates (as YYYYMMDD, so '9 February 2026' in a claim matches '2026-02-09')."""
    nums = [n.value for n in find_numbers(text)]
    nums += [float(WORD_NUMBERS[m.group(1).lower()]) for m in _WORD_RE.finditer(text)]
    nums += [float(d.value) for d in find_dates(text)]
    return nums


# ---------------------------------------------------------------------------
# Dates and spelled-out counts
# ---------------------------------------------------------------------------

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_WORD_ALT = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
_WORD_RE = re.compile(rf"\b({_WORD_ALT})\b(?!-)", re.IGNORECASE)
# "six of eight targets", "five out of the 12 participants": a count claim to check
_COUNT_RE = re.compile(
    rf"\b(?P<a>{_WORD_ALT}|\d+)\s+(?:out\s+)?of\s+(?:the\s+|all\s+|its\s+|their\s+|these\s+|those\s+)?"
    rf"(?P<b>{_WORD_ALT}|\d+)\b",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10,
    "nov": 11, "dec": 12,
}  # fmt: skip
_MON = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE_RE = re.compile(
    r"(?<![\w-])(?P<y1>\d{4})-(?P<m1>\d{2})-(?P<d1>\d{2})(?![\w-])"
    rf"|\b(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<mon2>{_MON})\.?,?\s+(?P<y2>\d{{4}})\b"
    rf"|\b(?P<mon3>{_MON})\.?\s+(?P<d3>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y3>\d{{4}})\b",
    re.IGNORECASE,
)


def find_dates(text: str) -> list[Num]:
    """Full dates as Nums whose value is YYYYMMDD ('2026-02-09', '9 February 2026', 'Feb 9, 2026')."""
    out: list[Num] = []
    for m in _DATE_RE.finditer(text):
        if m.group("y1"):
            y, mo, d = int(m.group("y1")), int(m.group("m1")), int(m.group("d1"))
        elif m.group("y2"):
            y, mo, d = int(m.group("y2")), _MONTHS[m.group("mon2").lower()], int(m.group("d2"))
        else:
            y, mo, d = int(m.group("y3")), _MONTHS[m.group("mon3").lower()], int(m.group("d3"))
        try:
            _dt.date(y, mo, d)
        except ValueError:
            continue
        out.append(Num(m.group(0), float(y * 10000 + mo * 100 + d), 0, False, 0, m.start()))
    return out


def find_count_words(text: str) -> list[Num]:
    """Spelled-out numbers in count phrases ('six of eight', 'three of the four').

    Digits are found by find_numbers; 'one of the …' is idiom ('one of the options'),
    so a leading 'one' is not treated as a count."""
    out: list[Num] = []
    for m in _COUNT_RE.finditer(text):
        for g in ("a", "b"):
            tok = m.group(g)
            if tok.isdigit() or (g == "a" and tok.lower() == "one"):
                continue
            out.append(Num(tok, float(WORD_NUMBERS[tok.lower()]), 0, False, 0, m.start(g)))
    return out


def now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n", 0, max_chars)
    if cut < max_chars * 0.6:
        cut = max_chars
    return text[:cut], True


def human_location(doc_type: str, anchor: str) -> str:
    """Anchor in words a reader can follow in the original file: t1.r3 -> 'table 1, row 3'."""
    m = re.fullmatch(r"page(\d+)(?:\.\d+)?", anchor)
    if m:
        return f"page {m.group(1)}"
    m = re.fullmatch(r"s(\d+)(?:\.(t|c)?(\d+|notes))?", anchor)
    if m and doc_type == "pptx":
        extra = {"t": " (table)", "c": " (chart)"}.get(m.group(2) or "", " (notes)" if anchor.endswith("notes") else "")
        return f"slide {m.group(1)}{extra}"
    if doc_type == "docx":
        m = re.fullmatch(r"t(\d+)(?:\.r(\d+))?", anchor)
        if m:
            return f"table {m.group(1)}" + (f", row {m.group(2)}" if m.group(2) else "")
        m = re.fullmatch(r"p(\d+)(?:-p(\d+))?", anchor)
        if m:
            return f"paragraph {m.group(1)}" + (f"–{m.group(2)}" if m.group(2) else "")
    if "!" in anchor:
        sheet, rng = anchor.rsplit("!", 1)
        return f"sheet {sheet.strip(chr(39))}, cells {rng}"
    m = re.fullmatch(r"L(\d+)(?:-L(\d+))?", anchor)
    if m:
        return f"lines {m.group(1)}" + (f"–{m.group(2)}" if m.group(2) else "")
    return anchor
