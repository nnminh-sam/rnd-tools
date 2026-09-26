"""Extraction anchors, incremental indexing, search and ref resolution on the demo."""

from rnd import api
from rnd.index.indexer import index_workspace
from rnd.index.search import exact, search
from rnd.index.store import Store


def test_all_demo_documents_indexed(ws):
    with Store(ws.index_path, readonly=True) as s:
        types = sorted(d.doc_type for d in s.all_docs())
    assert types == ["docx", "docx", "docx", "md", "pdf", "pdf", "pptx", "xlsx", "xlsx", "xlsx", "xlsx"]


def test_reindex_is_incremental(ws):
    rep = index_workspace(ws)
    assert rep.unchanged == 11 and not rep.added and not rep.updated


def test_search_finds_failure_across_documents(ws):
    hits = search(ws, ["armrest bracket crack", "KS-204 fatigue failure"], k=5)
    docs = {h.doc_id for h in hits}
    assert "tr-2026-031-p2-prototype-test-report" in docs
    assert "p2-design-review-2026-08-27" in docs


def test_search_diacritics_folding(fresh_ws):
    (fresh_ws.root / "notes" / "vn.md").write_text("# Ghi chú\n\nGhế văn phòng nhỏ gọn cho căn hộ.\n")
    index_workspace(fresh_ws)
    hits = search(fresh_ws, ["ghe van phong"], k=3)
    assert hits and hits[0].doc_id == "vn"


def test_exact_search_counts_blocks(ws):
    out = exact(ws, "KS-204")
    assert out.startswith("8 block(s)")


def test_resolve_anchor_forms(ws):
    with Store(ws.index_path, readonly=True) as s:
        _, blocks = s.resolve("p2-design-review-2026-08-27#s3")  # slide + its table + notes
        assert [b.anchor for b in blocks] == ["s3", "s3.t1", "s3.notes"]
        _, blocks = s.resolve("supplier-quotes-2026-07#Quotes!A14:O14")
        assert "KS-204" in blocks[0].text and len(blocks) == 1
        _, blocks = s.resolve("supplier-quotes-2026-07#Quotes!C14")  # single cell -> its row
        assert "ZincPro" in blocks[0].text
        _, blocks = s.resolve("2026-02-09-kickoff-project-kestrel#t1")
        assert blocks[0].anchor == "t1.r1" and any("USD 349" in b.text for b in blocks)
        _, blocks = s.resolve("customer-interviews-q2-2026#p19-p21")
        assert [b.anchor for b in blocks] == ["p19", "p20", "p21"]
        _, blocks = s.resolve("ideas-backlog#L10-L12")
        assert blocks and all(b.anchor.startswith("L") for b in blocks)


def test_read_and_outline_are_compact(ws):
    text = api.read(ws, ["tr-2026-031-p2-prototype-test-report#page2"], max_chars=400)
    assert text.startswith("── tr-2026-031") and "truncated" in text
    outline = api.outline(ws, "p2-design-review-2026-08-27")
    assert "[s6.c1] chart" in outline and "SQL tables:" in outline


def test_excel_header_detection_skips_title_rows(ws):
    with Store(ws.index_path, readonly=True) as s:
        t = {x["table_name"]: x for x in s.tables()}
    fatigue = t["seat_shell_materials_test_results__shell_fatigue"]
    assert fatigue["source_anchor"] == "Shell_Fatigue!A4:H28"
    assert fatigue["n_rows"] == 24
    survey = t["seating_survey_2026_responses__responses"]
    assert survey["n_rows"] == 240
    assert any("'n/a'" in n for n in survey["notes"])  # placeholders are reported, not hidden


def test_deleted_file_is_removed(fresh_ws):
    (fresh_ws.root / "notes" / "ideas-backlog.md").unlink()
    rep = index_workspace(fresh_ws)
    assert rep.removed == ["ideas-backlog (notes/ideas-backlog.md)"]


def test_exported_claude_conversations_are_not_indexed(fresh_ws):
    from rnd.index.indexer import index_workspace

    export = fresh_ws.root / "2026-09-26-115628-chat.txt"
    export.write_text(" ▐▛███▜▌   Claude Code v2.1.282\n❯ /rnd:ask what are the targets\n⏺ The targets are 120\n")
    rep = index_workspace(fresh_ws)
    assert not any("chat.txt" in a for a in rep.added)
