"""The verifier is the precision contract: these cases must never regress."""

from rnd.data.tables import run_sql
from rnd.verify import verify_markdown

KICKOFF = "2026-02-09-kickoff-project-kestrel"
REPORT = "tr-2026-031-p2-prototype-test-report"


def codes(ws, md):
    return sorted(i.code for i in verify_markdown(ws, md).issues if i.level == "error")


def test_correct_claims_pass(ws):
    calc = run_sql(
        ws,
        "select avg(cycles_to_failure) m from seat_shell_materials_test_results__shell_fatigue "
        "where material = 'rPP-50'",
    ).calc_id
    md = (
        f"The retail price target is USD 349 [@{KICKOFF}#t1.r2].\n\n"
        f'Unit 2 cracked at 38,500 cycles [@{REPORT}#page2 "Unit 2 failed at 38,500 cycles"].\n\n'
        f"The rPP-50 shell averaged 148,250 cycles [@calc:{calc}].\n\n"
        "Hypothesis: a steel bracket lasts 100,000 cycles.\n"
    )
    rep = verify_markdown(ws, md)
    assert rep.status == "PASS", rep.to_text()
    assert rep.figures_ok == rep.figures_checked == 4


def test_wrong_figure_is_an_error(ws):
    assert codes(ws, "Online sales are 65% of units [@home-office-seating-market-brief-2026#page2].") == [
        "figure-mismatch"
    ]


def test_uncited_figure_is_an_error(ws):
    assert codes(ws, "The mean assembly time was 11.6 minutes.") == ["uncited-figure"]


def test_paraphrased_quote_is_an_error(ws):
    md = '[@customer-interviews-q2-2026#p20 "armrests hit the desk so I can\'t pull in"]'
    assert codes(ws, "P05 complained " + md + ".") == ["bad-quote"]


def test_unknown_doc_and_anchor(ws):
    assert codes(ws, f"See [@nope#p1] and [@{KICKOFF}#p999].") == ["unknown-ref", "unknown-ref"]


def test_citation_after_full_stop_stays_with_its_sentence(ws):
    md = f"Assembly took 11.6 minutes on average. [@{REPORT}#page2] Online share is 62%. [@home-office-seating-market-brief-2026#page2]"
    assert verify_markdown(ws, md).status == "PASS"


def test_labelled_speculation_and_judgement_tables_are_exempt(ws):
    md = (
        "Assumption: tooling costs fall 20% at 10,000 units.\n\n"
        "| Idea | Score (judgement) |\n|---|---|\n| Captive screws | 4 |\n"
    )
    rep = verify_markdown(ws, md)
    assert rep.status == "PASS" and rep.units_exempt == 2


def test_sources_section_is_not_checked(ws):
    assert verify_markdown(ws, "# Report\n\n## Sources\n- Something 2025, p. 44\n").status == "PASS"


def test_whole_table_citation_warns_broad_ref(ws):
    rep = verify_markdown(ws, f"The retail price target is USD 349 [@{KICKOFF}#t1].")
    assert rep.status == "WARN"
    assert [i.code for i in rep.issues] == ["broad-ref"]


def test_dates_match_as_one_figure_including_the_document_date(ws):
    # the kickoff date is only in the file name "2026-02-09 Kickoff - Project KESTREL.docx"
    ok = f"At the kickoff on 9 February 2026 the retail price target was set at USD 349 [@{KICKOFF}#t1.r2]."
    assert verify_markdown(ws, ok).status == "PASS", verify_markdown(ws, ok).to_text()
    wrong = f"At the kickoff on 10 February 2026 the retail price target was set at USD 349 [@{KICKOFF}#t1.r2]."
    assert codes(ws, wrong) == ["figure-mismatch"]


def test_spelled_out_counts_are_checked(ws):
    # page 1 says "Nine tests were run … Seven tests passed and two failed"
    assert verify_markdown(ws, f"Seven of nine P2 tests passed [@{REPORT}#page1].").status == "PASS"
    assert codes(ws, f"Eight of nine P2 tests passed [@{REPORT}#page1].") == ["figure-mismatch"]
    assert verify_markdown(ws, f"Option B is one of the options on the table [@{REPORT}#page1].").status == "PASS"


def test_table_rows_inherit_the_caption_citation(ws):
    calc = run_sql(
        ws,
        "select material, round(avg(cycles_to_failure)) mean_cycles "
        "from seat_shell_materials_test_results__shell_fatigue group by 1 order by 1",
    ).calc_id
    ok = f"Mean cycles per material [@calc:{calc}]:\n\n| Material | Mean |\n|---|---|\n| rPP-50 | 148,250 |\n"
    assert verify_markdown(ws, ok).status == "PASS", verify_markdown(ws, ok).to_text()
    heading = f"### Shell fatigue [@calc:{calc}]\n\n| Material | Mean |\n|---|---|\n| rPP-50 | 148,250 |\n"
    assert verify_markdown(ws, heading).status == "PASS"
    wrong = ok.replace("148,250", "150,250")
    assert codes(ws, wrong) == ["figure-mismatch"]
    # a plain sentence above a table is not a caption: rows still need their own citations
    loose = f"The data is below [@calc:{calc}].\n\n| Material | Mean |\n|---|---|\n| rPP-50 | 148,250 |\n"
    assert codes(ws, loose) == ["uncited-figure"]


def test_calc_ids_are_labels_not_figures(ws):
    assert (
        verify_markdown(ws, "## Method\n\n- calc:8 — per-material means from the Shell_Fatigue sheet").status == "PASS"
    )


def test_missing_index_is_one_error(tmp_path):
    from rnd.workspace import init_workspace

    empty = init_workspace(tmp_path, "empty")
    rep = verify_markdown(empty, f"A [@{KICKOFF}#p1]. B [@{KICKOFF}#p2]. C [@{REPORT}#page1].")
    assert [i.code for i in rep.errors] == ["no-index"]
