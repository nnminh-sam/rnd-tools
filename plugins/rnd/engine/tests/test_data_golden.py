"""SQL over the demo must reproduce the generator's golden facts exactly.

If a test here fails after changing tools/build_demo.py, regenerate the demo and the
golden file (`uv run python tools/build_demo.py`) — never edit numbers by hand.
"""

from pathlib import Path

import pytest

from rnd.data.tables import SqlError, load_calc, run_sql

ENGINE = Path(__file__).resolve().parents[1]

QUOTES = "supplier_quotes_2026_07__quotes"

CONFIG_SQL = """
with opt as (select * from {q} where option = '{opt}' or part_no in ({alts})),
replaced as (select trim(unnest(string_split(replaces, ';'))) as part_no from opt where replaces is not null),
parts as (
  select * from {q} where option = 'baseline' and part_no not in (select part_no from replaced)
  union all select * from opt
)
select round(sum(qty_per_chair * unit_price_usd_5k), 2) as unit_cost,
       round(100 * sum(qty_per_chair * mass_kg_each * recycled_content_pct / 100) filter (where part_no <> 'KS-180')
             / sum(qty_per_chair * mass_kg_each) filter (where part_no <> 'KS-180'), 2) as recycled_pct
from parts
"""


def test_shell_fatigue_means(ws, golden):
    res = run_sql(
        ws,
        "select material, avg(cycles_to_failure) m, min(cycles_to_failure) lo, "
        "count(*) filter (where cycles_to_failure >= 120000) n_ok "
        "from seat_shell_materials_test_results__shell_fatigue group by material",
    )
    rows = {r[0]: r[1:] for r in res.rows}
    for material, mean in golden["shell_mean_cycles"].items():
        assert round(rows[material][0], 2) == mean
        assert rows[material][1] == golden["shell_min_cycles"][material]
        assert rows[material][2] == golden["shell_samples_passing"][material]


@pytest.mark.parametrize(
    "name,opt,alts",
    [
        ("baseline_P2", "baseline", ""),
        ("option_A", "A", ""),
        ("option_B", "B", ""),
        ("option_C", "C", ""),
        ("baseline_P2_eco", "baseline", "'KS-130-ECO'"),
        ("option_B_eco", "B", "'KS-130-ECO'"),
        ("option_C_eco_hanoi_shell", "C", "'KS-130-ECO','KS-101-ALT'"),
    ],
)
def test_bom_configurations(ws, golden, name, opt, alts):
    sql = CONFIG_SQL.format(q=QUOTES, opt=opt if opt != "baseline" else "__none__", alts=alts or "''")
    res = run_sql(ws, sql, save=False)
    assert res.rows[0] == (golden["configs"][name]["unit_cost_usd"], golden["configs"][name]["recycled_pct"])


def test_competitor_filter(ws, golden):
    res = run_sql(
        ws,
        "select model from competitor_benchmark_2026__benchmark "
        "where price_usd < 400 and base_diameter_mm <= 600 order by model",
        save=False,
    )
    assert [r[0] for r in res.rows] == golden["competitors_under_400_base_le_600"]


def test_interview_counts_from_word_table(ws, golden):
    res = run_sql(
        ws,
        "select count(*) filter (where chair_too_bulky_for_the_room = 'Y'), "
        "count(*) filter (where armrests_collide_with_desk_want_flip_up = 'Y') "
        "from customer_interviews_q2_2026__table_2",
        save=False,
    )
    counts = golden["interview_theme_counts"]
    assert res.rows[0] == (counts["footprint"], counts["armrests"])


def test_calc_is_saved_with_provenance(ws):
    res = run_sql(ws, "select count(*) as n from competitor_benchmark_2026__benchmark")
    calc = load_calc(ws, res.calc_id)
    assert calc["rows"] == [[8]]
    assert calc["source_files"] == ["sources/competitors/Competitor benchmark 2026.xlsx"]


def test_sql_is_read_only_and_sandboxed(ws):
    with pytest.raises(SqlError):
        run_sql(ws, "drop table competitor_benchmark_2026__benchmark")
    with pytest.raises(SqlError):
        run_sql(ws, "select * from read_csv('/etc/hosts')")


def test_tutorial_doc_ids_and_target_anchors_match_the_index(ws):
    """TUTORIAL.md tells users exact doc ids and anchors; they must exist."""
    import sys

    sys.path.insert(0, str(ENGINE / "tools"))
    import build_demo

    from rnd.index.store import Store

    with Store(ws.index_path, readonly=True) as store:
        paths = {d.doc_id: d.path for d in store.all_docs()}
        assert {did: path for path, did, _ in build_demo.TUTORIAL_DOCS} == paths
        for i, (name, value, _why) in enumerate(build_demo.TARGETS):
            _doc, blocks = store.resolve(f"2026-02-09-kickoff-project-kestrel#t1.r{i + 2}")
            assert name in blocks[0].text and value in blocks[0].text
