"""Generate the KESTREL demo workspace (synthetic furniture R&D project).

    uv run python tools/build_demo.py            # writes ../demo/kestrel-chair
    uv run python tools/build_demo.py --check    # regenerate into a temp dir and diff facts

Every figure lives in the DATA section below and is written into several documents,
so cross-document questions have one correct answer. The generator also writes
tests/golden/kestrel.json with the expected answers used by the integration tests
and quoted in TUTORIAL.md. Change data here, never by hand in the output files.

All companies, people, products and figures are fictional (synthetic training data).
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from datetime import date, datetime
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ENGINE.parent / "demo" / "kestrel-chair"
GOLDEN = ENGINE / "tests" / "golden" / "kestrel.json"
FOOTER = "Aldermoor Furniture Co. — Project KESTREL — synthetic training data, all figures fictional"
FIXED_TIME = datetime(2026, 9, 1, 9, 0, 0)

# =============================================================================
# DATA
# =============================================================================

TEAM = [
    ("Mara Lindqvist", "Head of Product"),
    ("Tomasz Wierzbicki", "Lead Mechanical Engineer"),
    ("Aiko Tanaka", "Industrial Designer"),
    ("Daniel Okafor", "Sourcing Manager"),
    ("Priya Raman", "Product Marketing"),
    ("Lucas Moreau", "Finance Controller"),
]

TARGETS = [
    # (target, value, rationale)
    ("Retail price", "USD 349", "Sits in the USD 200–399 band that holds 34% of unit sales (market brief)."),
    ("Unit cost (landed, incl. packaging)", "≤ USD 120", "Keeps gross margin above 60% at USD 349 after channel fees."),
    ("Base diameter", "≤ 600 mm", "Fits a 1.2 m wide desk niche; typical task chairs are 640–700 mm."),
    ("Seat width", "460–490 mm", "Covers the 5th–95th percentile of the target users."),
    ("Maximum user weight", "125 kg", "Matches the heaviest competitor claim in our price band."),
    ("Recycled content", "≥ 50% by weight", "Brand commitment for all 2027 launches; packaging excluded."),
    ("Shipping carton", "≤ 0.12 m³, single box", "Parcel-carrier limit without surcharge."),
    ("Assembly time", "≤ 10 min, included hex key only", "Assembly problems cause 12% of online returns."),
    ("Seat shell fatigue", "≥ 120,000 cycles", "Internal test TP-07."),
    ("Armrest fatigue", "≥ 60,000 cycles", "Internal test TP-12."),
    ("Launch", "Q2 2027", "Aligned with the spring home-office promotion."),
]

INTERVIEW_THEMES = [
    ("footprint", "Chair too bulky for the room"),
    ("back", "Lower-back discomfort after 3+ hours"),
    ("assembly", "Frustrating assembly"),
    ("armrests", "Armrests collide with desk / want flip-up"),
    ("sustainability", "Wants sustainable materials"),
    ("price", "Price-sensitive (would not pay > USD 400)"),
]

PARTICIPANTS = [
    # id, age, city, office m2, hours, current chair, paid, themes, summary, quote
    (
        "P01",
        34,
        "Rotterdam",
        6.0,
        7.5,
        "gaming chair",
        289,
        {"footprint", "back", "armrests"},
        "Works in a converted closet; the chair's base blocks the door.",
        "My chair is wider than the room is deep, I have to move it to close the door.",
    ),
    (
        "P02",
        41,
        "Chicago",
        9.5,
        6.0,
        "second-hand office chair",
        60,
        {"back", "price"},
        "Chronic lower-back pain; bought a cheap used chair and regrets it.",
        "After lunch my lower back starts to ache and by five I am standing at the kitchen counter.",
    ),
    (
        "P03",
        29,
        "Warsaw",
        5.5,
        8.0,
        "IKEA-style mesh chair",
        149,
        {"footprint", "assembly", "sustainability"},
        "Assembled the chair twice because the backrest was mounted backwards.",
        "The instructions were only pictures and I put the back on the wrong way, twice.",
    ),
    (
        "P04",
        52,
        "Lyon",
        11.0,
        5.0,
        "dining chair",
        0,
        {"back", "sustainability", "price"},
        "Uses a dining chair; hesitant to spend on 'office furniture' at home.",
        "I would pay a bit more for recycled materials, but not four hundred euros for a chair.",
    ),
    (
        "P05",
        37,
        "Seattle",
        7.0,
        9.0,
        "premium ergonomic chair",
        1150,
        {"footprint", "armrests"},
        "Owns a premium chair that is comfortable but dominates the small room.",
        "It is a great chair, it is just enormous. The armrests hit the desk so I cannot pull in.",
    ),
    (
        "P06",
        45,
        "Manchester",
        6.5,
        7.0,
        "basic task chair",
        119,
        {"footprint", "back", "assembly"},
        "Lower-back pain; says assembly took 40 minutes with a borrowed screwdriver.",
        "It said ten minutes on the box. It took me forty and a screwdriver I did not have.",
    ),
    (
        "P07",
        26,
        "Berlin",
        4.5,
        8.5,
        "stool",
        35,
        {"footprint", "back", "price", "sustainability"},
        "Works from a shared flat; space and budget are the constraints.",
        "Anything with a huge star base simply does not fit next to my bed.",
    ),
    (
        "P08",
        58,
        "Toronto",
        12.0,
        4.5,
        "executive leather chair",
        420,
        {"back", "armrests"},
        "Big room, but armrests stop the chair sliding under the desk.",
        "I want armrests that fold away when I am typing, then come back when I read.",
    ),
    (
        "P09",
        31,
        "Madrid",
        8.0,
        7.0,
        "mesh task chair",
        199,
        {"footprint", "assembly", "sustainability"},
        "Cares about materials; skeptical of green marketing claims.",
        "Everyone says eco now. Tell me the percentage of recycled plastic and I will believe you.",
    ),
    (
        "P10",
        48,
        "Austin",
        10.0,
        6.5,
        "gaming chair",
        349,
        {"back", "armrests", "price"},
        "Gaming chair looked good online but causes back pain.",
        "The lumbar pillow keeps sliding down, I ended up throwing it away.",
    ),
    (
        "P11",
        39,
        "Copenhagen",
        7.5,
        7.5,
        "design chair",
        610,
        {"footprint", "assembly", "armrests"},
        "Values design; frustrated by complex assembly of a design chair.",
        "Twelve bolts, three sizes, and one of them was missing.",
    ),
    (
        "P12",
        33,
        "Singapore",
        5.0,
        9.5,
        "basic task chair",
        139,
        {"footprint", "assembly", "sustainability", "price"},
        "Very small apartment; would switch for a compact chair under USD 350.",
        "If it is compact, comfortable and under three-fifty I would switch tomorrow.",
    ),
]

COMPETITORS = [
    # model, brand, price, base mm, seat mm, weight kg, max kg, armrests, lumbar, recycled %, warranty, assembly min, rating, reviews
    ("Brisk Lite", "Norvo", 229, 640, 470, 12.9, 110, "fixed", "none", 10, 2, 18, 3.9, 2140),
    ("Ergon 3", "Halvard", 549, 690, 500, 19.5, 136, "4D", "adjustable", 35, 12, 25, 4.6, 5310),
    ("Studio Task", "Maple & Co", 389, 620, 480, 15.2, 120, "2D", "fixed", 20, 5, 15, 4.2, 1870),
    ("FlexiSit Mini", "Tokka", 279, 580, 450, 11.4, 100, "flip-up", "none", 0, 2, 12, 3.8, 960),
    ("Axis Home", "Pellmann", 459, 650, 490, 17.8, 130, "3D", "adjustable", 45, 10, 20, 4.5, 3420),
    ("Pivot One", "Corva", 319, 600, 465, 13.6, 115, "flip-up", "fixed", 25, 5, 14, 4.1, 1250),
    ("Nook Chair", "Lumen Home", 349, 560, 455, 10.8, 110, "none", "fixed", 30, 3, 8, 4.0, 780),
    ("Terra Task", "Greenline", 499, 640, 480, 16.1, 125, "2D", "adjustable", 72, 7, 22, 4.3, 1105),
]

SHELL_FATIGUE = {
    # material -> list of (cycles, failure mode)
    "PP-GF30 virgin": [
        (178400, "crack at rear mounting boss"),
        (165200, "crack at rear mounting boss"),
        (190100, "crack at front edge rib"),
        (171800, "crack at rear mounting boss"),
        (183600, "crack at front edge rib"),
        (168900, "crack at rear mounting boss"),
    ],
    "rPP-50": [
        (151200, "crack at rear mounting boss"),
        (139800, "crack at rear mounting boss"),
        (147600, "crack at front edge rib"),
        (158300, "crack at rear mounting boss"),
        (142900, "crack at rear mounting boss"),
        (149700, "crack at front edge rib"),
    ],
    "rPP-100": [
        (98700, "crack at rear mounting boss"),
        (121400, "crack at front edge rib"),
        (88300, "delamination at weld line"),
        (112600, "crack at rear mounting boss"),
        (131900, "crack at front edge rib"),
        (94100, "delamination at weld line"),
    ],
    "PA11-GF bio": [
        (200000, "runout (no failure)"),
        (196300, "crack at rear mounting boss"),
        (200000, "runout (no failure)"),
        (200000, "runout (no failure)"),
        (188500, "crack at front edge rib"),
        (200000, "runout (no failure)"),
    ],
}
SHELL_TARGET = 120000

MATERIALS = [
    # material, description, recycled %, cost USD/kg, kg CO2e/kg, density, shell mass kg
    ("PP-GF30 virgin", "Polypropylene, 30% glass fibre, virgin", 0, 2.10, 2.9, 1.14, 1.35),
    ("rPP-50", "PP-GF30 with 50% post-consumer recycled PP", 50, 2.25, 1.9, 1.15, 1.35),
    ("rPP-100", "PP-GF30 with 100% post-consumer recycled PP", 100, 2.45, 1.0, 1.16, 1.40),
    ("PA11-GF bio", "Bio-based polyamide 11, glass filled", 0, 7.80, 2.4, 1.26, 1.20),
]

FOAM = [
    ("PU-45 virgin", 45, 6.5, 0, 4.90),
    ("PU-45 R30", 45, 7.8, 30, 5.35),
    ("PU-55 R30", 55, 5.9, 30, 6.10),
]

# Bill of materials quotes (price at 5,000 units/yr is the planning basis).
# option: baseline = P2 configuration; A/B/C = armrest fixes; alt = alternatives
QUOTES = [
    # part_no, part, supplier, country, option, replaces, qty, mass kg each, recycled %, price@5k, tooling, lead wks
    ("KS-101", "Seat shell rPP-50", "Baltic Polymers", "PL", "baseline", "", 1, 1.35, 50, 5.20, 38000, 10),
    (
        "KS-101-ALT",
        "Seat shell rPP-50 (second source)",
        "Hanoi Precision Plastics",
        "VN",
        "alt",
        "KS-101",
        1,
        1.35,
        50,
        4.45,
        29000,
        14,
    ),
    ("KS-102", "Backrest frame rPP-50", "Baltic Polymers", "PL", "baseline", "", 1, 1.10, 50, 4.60, 31000, 10),
    ("KS-110", "Mesh back textile rPET", "Textura", "PT", "baseline", "", 1, 0.35, 100, 7.90, 0, 6),
    ("KS-120", "Seat foam PU-45 R30", "FoamTec", "PL", "baseline", "", 1, 0.55, 30, 5.35, 6500, 5),
    ("KS-121", "Seat fabric rPET", "Textura", "PT", "baseline", "", 1, 0.20, 100, 3.95, 0, 6),
    ("KS-130", "Synchro-tilt mechanism", "Mechanika", "CZ", "baseline", "", 1, 2.90, 40, 21.50, 0, 12),
    (
        "KS-130-ECO",
        "Synchro-tilt mechanism EcoLine (70% recycled steel)",
        "Mechanika",
        "CZ",
        "alt",
        "KS-130",
        1,
        2.90,
        70,
        22.80,
        0,
        14,
    ),
    ("KS-140", "Gas lift class 4", "LiftCo", "DE", "baseline", "", 1, 1.25, 25, 7.40, 0, 8),
    (
        "KS-150",
        "5-star base, recycled aluminium, 592 mm",
        "AluCast",
        "PL",
        "baseline",
        "",
        1,
        2.60,
        75,
        17.90,
        42000,
        11,
    ),
    (
        "KS-150-ALT",
        "5-star base, PA6-GF nylon, 592 mm",
        "Hanoi Precision Plastics",
        "VN",
        "alt",
        "KS-150",
        1,
        2.10,
        0,
        9.80,
        27000,
        14,
    ),
    ("KS-160", "Casters 50 mm (set of 5)", "RollOn", "IT", "baseline", "", 1, 0.75, 20, 4.80, 0, 6),
    ("KS-204", "Armrest bracket, zinc die-cast (P2 design)", "ZincPro", "CZ", "baseline", "", 2, 0.28, 0, 1.30, 0, 8),
    (
        "KS-204A",
        "Armrest bracket, zinc die-cast, R2.0 radius + rib",
        "ZincPro",
        "CZ",
        "A",
        "KS-204",
        2,
        0.30,
        0,
        1.48,
        4800,
        9,
    ),
    ("KS-204B", "Armrest bracket, stamped steel", "Stahlform", "DE", "B", "KS-204", 2, 0.34, 30, 1.85, 11500, 10),
    (
        "KS-205",
        "Armrest post and pad, fixed height",
        "Baltic Polymers",
        "PL",
        "baseline",
        "",
        2,
        0.62,
        50,
        2.20,
        14000,
        10,
    ),
    (
        "KS-205C",
        "Flip-up armrest assembly incl. bracket",
        "Mechanika",
        "CZ",
        "C",
        "KS-204;KS-205",
        2,
        0.95,
        20,
        5.95,
        26000,
        16,
    ),
    ("KS-170", "Fasteners and hex key kit", "FixPoint", "PL", "baseline", "", 1, 0.25, 0, 1.15, 0, 4),
    ("KS-180", "Carton and inserts (0.118 m³)", "PackRight", "PL", "baseline", "", 1, 0.0, 90, 4.60, 1200, 3),
    ("KS-900", "Final assembly and QC labour", "Aldermoor Gdańsk", "PL", "baseline", "", 1, 0.0, 0, 12.60, 0, 0),
    (
        "KS-910",
        "Inbound freight and duty allocation",
        "Aldermoor Logistics",
        "PL",
        "baseline",
        "",
        1,
        0.0,
        0,
        12.90,
        0,
        0,
    ),
]
UNIT_COST_TARGET = 120.0
RECYCLED_TARGET = 50.0

ASSEMBLY_TIMES = [("Tester 1", 9.1), ("Tester 2", 10.8), ("Tester 3", 11.4), ("Tester 4", 12.5), ("Tester 5", 14.2)]

P2_TESTS = [
    ("T1", "Seat drop impact", "TP-02", "No damage after 10 drops (75 kg)", "No damage (3/3 units)", "PASS"),
    ("T2", "Seat shell cyclic", "TP-07", "120,000 cycles", "120,000 cycles, no failure (3/3 units)", "PASS"),
    ("T3", "Backrest cyclic", "TP-08", "120,000 cycles", "120,000 cycles, no failure (3/3 units)", "PASS"),
    ("T4", "Armrest vertical static", "TP-11", "750 N, no failure", "750 N, no failure (3/3 units)", "PASS"),
    (
        "T5",
        "Armrest cyclic",
        "TP-12",
        "60,000 cycles",
        "Crack at 38,500 cycles (unit 2) and 41,200 cycles (unit 4)",
        "FAIL",
    ),
    ("T6", "Base static load", "TP-14", "11,120 N, no failure", "11,120 N, no failure (3/3 units)", "PASS"),
    ("T7", "Rear stability", "TP-16", "No tip-over", "No tip-over (3/3 units)", "PASS"),
    ("T8", "Caster durability", "TP-18", "98,000 cycles", "98,000 cycles, no failure (3/3 units)", "PASS"),
    ("T9", "Assembly time", "5 untrained testers", "≤ 10 min", "Mean 11.6 min (range 9.1–14.2 min)", "FAIL"),
]

# =============================================================================
# derived facts (single source of truth for tests and the tutorial)
# =============================================================================


def config_parts(option: str | None = None, alts: tuple[str, ...] = ()) -> list[tuple]:
    parts = [q for q in QUOTES if q[4] == "baseline"]
    chosen = [q for q in QUOTES if (option and q[4] == option) or q[0] in alts]
    for q in chosen:
        replaced = set(q[5].split(";")) if q[5] else set()
        parts = [p for p in parts if p[0] not in replaced] + [q]
    return parts


def unit_cost(parts) -> float:
    return round(sum(p[6] * p[9] for p in parts), 2)


def recycled_pct(parts) -> float:
    mass = sum(p[6] * p[7] for p in parts if p[0] != "KS-180")  # packaging excluded
    rec = sum(p[6] * p[7] * p[8] / 100 for p in parts if p[0] != "KS-180")
    return round(100 * rec / mass, 2)


def golden_facts() -> dict:
    shell = {m: [c for c, _ in rows] for m, rows in SHELL_FATIGUE.items()}
    configs = {}
    for name, opt, alts in [
        ("baseline_P2", None, ()),
        ("option_A", "A", ()),
        ("option_B", "B", ()),
        ("option_C", "C", ()),
        ("baseline_P2_eco", None, ("KS-130-ECO",)),
        ("option_A_eco", "A", ("KS-130-ECO",)),
        ("option_B_eco", "B", ("KS-130-ECO",)),
        ("option_C_eco", "C", ("KS-130-ECO",)),
        ("option_C_eco_hanoi_shell", "C", ("KS-130-ECO", "KS-101-ALT")),
    ]:
        parts = config_parts(opt, alts)
        configs[name] = {
            "unit_cost_usd": unit_cost(parts),
            "recycled_pct": recycled_pct(parts),
            "mass_kg": round(sum(p[6] * p[7] for p in parts if p[0] != "KS-180"), 2),
        }
    counts = {key: sum(key in p[7] for p in PARTICIPANTS) for key, _ in INTERVIEW_THEMES}
    small = [c for c in COMPETITORS if c[2] < 400 and c[3] <= 600]
    return {
        "targets": {
            "retail_price_usd": 349,
            "unit_cost_max_usd": UNIT_COST_TARGET,
            "base_max_mm": 600,
            "recycled_min_pct": RECYCLED_TARGET,
            "assembly_max_min": 10,
            "shell_cycles": SHELL_TARGET,
            "armrest_cycles": 60000,
        },
        "interview_theme_counts": counts,
        "interviews_total": len(PARTICIPANTS),
        "shell_mean_cycles": {m: round(statistics.mean(v), 2) for m, v in shell.items()},
        "shell_min_cycles": {m: min(v) for m, v in shell.items()},
        "shell_samples_passing": {m: sum(c >= SHELL_TARGET for c in v) for m, v in shell.items()},
        "competitors_under_400_base_le_600": sorted(c[0] for c in small),
        "competitors_recycled_ge_50": sorted(c[0] for c in COMPETITORS if c[9] >= 50),
        "assembly_mean_min": round(statistics.mean(t for _, t in ASSEMBLY_TIMES), 2),
        "armrest_crack_cycles": [38500, 41200],
        "configs": configs,
    }


# =============================================================================
# writers
# =============================================================================


def _docx_base(title: str, subtitle: str):
    import docx
    from docx.shared import Pt

    d = docx.Document()
    d.core_properties.title = title
    d.core_properties.author = "Aldermoor Furniture Co."
    d.core_properties.created = FIXED_TIME
    d.core_properties.modified = FIXED_TIME
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    d.add_heading(title, level=0)
    d.add_paragraph(subtitle)
    d.sections[0].footer.paragraphs[0].text = FOOTER
    return d


def _docx_table(d, header, rows):
    t = d.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = str(h)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    return t


def write_kickoff(path: Path) -> None:
    d = _docx_base(
        "Project KESTREL — Kickoff Meeting Notes", "Date: 9 February 2026 · Location: Gdańsk studio and video call"
    )
    d.add_heading("Attendees", 1)
    for name, role in TEAM:
        d.add_paragraph(f"{name} — {role}", style="List Bullet")
    d.add_heading("Purpose", 1)
    d.add_paragraph(
        "Kick off development of KESTREL, a compact ergonomic task chair for people who work from small home offices. "
        "The product must deliver full-size ergonomics in a smaller footprint, be easy to assemble, and meet the "
        "Aldermoor 2027 recycled-content commitment."
    )
    d.add_heading("Why now", 1)
    d.add_paragraph(
        "Online task-chair returns are costly: the market brief attributes 23% of returns to the chair being too big "
        "for the space and 12% to assembly problems. Customer service logged 1,840 complaints about chair size in 2025."
    )
    d.add_heading("Product targets", 1)
    _docx_table(d, ["Target", "Value", "Rationale"], TARGETS)
    d.add_heading("Decisions", 1)
    for text in [
        "D1: Target segment is home-office workers with rooms under 10 m²; commercial contract seating is out of scope.",
        "D2: Evaluate flip-up armrests as an option; fixed armrests remain the baseline for P1 and P2.",
        "D3: Seat shell material shortlist is PP-GF30 virgin (reference), rPP-50, rPP-100 and PA11-GF bio. "
        "Test program TP-07 decides the material.",
        "D4: Planning volume is 5,000 units in year one; all costs are quoted at that volume.",
    ]:
        d.add_paragraph(text, style="List Bullet")
    d.add_heading("Risks", 1)
    for text in [
        "R1: Recycled polypropylene may not reach the 120,000-cycle shell fatigue target.",
        "R2: Recycled materials and aluminium could push the unit cost above USD 120.",
        "R3: A smaller base could compromise rear stability; test TP-16 must pass.",
    ]:
        d.add_paragraph(text, style="List Bullet")
    d.add_heading("Actions", 1)
    _docx_table(
        d,
        ["Action", "Owner", "Due"],
        [
            ("Run shell material fatigue program TP-07", "Tomasz Wierzbicki", "2026-04-30"),
            ("Conduct 12 customer interviews", "Priya Raman", "2026-05-31"),
            ("Collect supplier quotes at 5k volume", "Daniel Okafor", "2026-07-15"),
            ("Build P2 prototypes (6 units)", "Aiko Tanaka", "2026-07-31"),
        ],
    )
    d.save(path)


def write_sync(path: Path, facts: dict) -> None:
    d = _docx_base(
        "KESTREL Weekly Sync — 20 August 2026",
        "Attendees: Mara Lindqvist, Tomasz Wierzbicki, Daniel Okafor, Priya Raman, Lucas Moreau",
    )
    d.add_heading("P2 test status", 1)
    d.add_paragraph(
        "Test report TR-2026-031 is out. Seven of nine tests passed. The armrest cyclic test T5 failed: the zinc "
        "bracket KS-204 cracked at 38,500 and 41,200 cycles against a 60,000-cycle target. Assembly time T9 also "
        "failed with a mean of 11.6 minutes."
    )
    d.add_heading("Armrest options discussed", 1)
    d.add_paragraph(
        "Option A: keep zinc die-casting, increase the inner radius to R2.0 mm and add a rib.", style="List Bullet"
    )
    d.add_paragraph(
        "Option B: switch the bracket to stamped steel from a new supplier (Stahlform).", style="List Bullet"
    )
    d.add_paragraph(
        "Option C: replace fixed armrests with a flip-up armrest assembly from Mechanika.", style="List Bullet"
    )
    d.add_heading("Positions", 1)
    d.add_paragraph(
        "Lucas Moreau (Finance): any option must keep the landed unit cost at or below USD 120 at the 5,000-unit volume. "
        "He asked Sourcing for costed configurations before the design review."
    )
    d.add_paragraph(
        "Priya Raman (Marketing): prefers Option C because 5 of 12 interviewees complained about armrests hitting the desk."
    )
    d.add_paragraph(
        "Tomasz Wierzbicki (Engineering): Option A does not address the casting porosity seen in the failure analysis; "
        "Option B removes both suspected causes."
    )
    d.add_paragraph(
        "Daniel Okafor (Sourcing): the current BOM misses the 50% recycled-content target; Mechanika offers an EcoLine "
        "mechanism with 70% recycled steel at a higher price."
    )
    d.add_heading("Decision", 1)
    d.add_paragraph("No decision taken. Decision deferred to the P2 design review on 27 August 2026.")
    d.save(path)


def write_interviews(path: Path) -> None:
    d = _docx_base(
        "Customer Interviews Q2 2026 — Home-office seating",
        "12 remote interviews, 14 April – 22 May 2026 · Moderator: Priya Raman",
    )
    d.add_heading("Method", 1)
    d.add_paragraph(
        "Semi-structured 45-minute video interviews with people who work from home at least three days a week. "
        "Participants were recruited from the Aldermoor newsletter and screened for room size and chair ownership. "
        "Each interview was coded against six pain-point themes by two researchers."
    )
    d.add_heading("Participants", 1)
    _docx_table(
        d,
        ["ID", "Age", "City", "Office m²", "Hours seated/day", "Current chair", "Price paid USD"],
        [(p[0], p[1], p[2], p[3], p[4], p[5], p[6]) for p in PARTICIPANTS],
    )
    d.add_heading("Interview summaries", 1)
    for p in PARTICIPANTS:
        d.add_heading(f"{p[0]} — {p[2]}", 2)
        d.add_paragraph(p[8])
        d.add_paragraph(f"“{p[9]}”")
    d.add_heading("Coded pain points", 1)
    d.add_paragraph("Y = theme raised by the participant (agreed by both coders).")
    header = ["Participant"] + [label for _, label in INTERVIEW_THEMES]
    _docx_table(
        d, header, [[p[0]] + ["Y" if key in p[7] else "N" for key, _ in INTERVIEW_THEMES] for p in PARTICIPANTS]
    )
    counts = {key: sum(key in p[7] for p in PARTICIPANTS) for key, _ in INTERVIEW_THEMES}
    d.add_heading("Synthesis", 1)
    d.add_paragraph(
        f"The most frequent theme is footprint: {counts['footprint']} of 12 participants said their chair is too bulky "
        f"for the room. Lower-back discomfort follows with {counts['back']} of 12."
    )
    d.add_paragraph(
        f"Assembly frustration was raised by {counts['assembly']} participants, and {counts['armrests']} described "
        "armrests that collide with the desk; two of them explicitly asked for armrests that fold away."
    )
    d.add_paragraph(
        f"{counts['sustainability']} participants want sustainable materials, but they ask for concrete recycled-content "
        f"figures rather than generic claims. {counts['price']} participants would not pay more than USD 400."
    )
    d.save(path)


def write_survey(path: Path) -> None:
    import openpyxl
    from openpyxl.styles import Font

    rng = random.Random(20260504)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Responses"
    ws["A1"] = "Aldermoor home-office seating survey 2026 — raw responses"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "Fielded 2026-05-04 to 2026-05-25 · n = 240 · synthetic training data"
    header = [
        "respondent_id",
        "region",
        "age_band",
        "home_office_m2",
        "hours_seated_per_day",
        "current_chair_price_usd",
        "back_pain_score_0_10",
        "wtp_usd",
        "imp_comfort",
        "imp_footprint",
        "imp_sustainability",
        "imp_price",
        "imp_assembly",
        "would_consider_kestrel",
    ]
    ws.append([])
    ws.append(header)
    for c in ws[4]:
        c.font = Font(bold=True)
    regions = ["North America"] * 5 + ["Europe"] * 4 + ["Asia-Pacific"] * 3
    ages = ["18-29", "30-39", "40-49", "50-64"]
    for i in range(1, 241):
        m2 = round(min(16.0, max(3.5, rng.gauss(8.2, 2.6))), 1)
        hours = round(min(11.0, max(3.0, rng.gauss(7.1, 1.4))), 1)
        pain = max(0, min(10, round(rng.gauss(4.2 + (hours - 7) * 0.6, 2.0))))
        wtp = int(round(min(650, max(120, rng.gauss(318, 72))) / 5.0) * 5)
        foot = max(1, min(5, round(5.6 - m2 * 0.32 + rng.gauss(0, 0.7))))
        sust = max(1, min(5, round(rng.gauss(3.4, 1.0))))
        consider = "Yes" if (foot >= 4 and wtp >= 300) else ("Maybe" if wtp >= 250 else "No")
        row = [
            f"R{i:03d}",
            rng.choice(regions),
            rng.choice(ages),
            m2,
            hours,
            int(round(max(0, rng.gauss(240, 160)) / 10) * 10),
            pain,
            wtp if i not in (17, 88, 203) else "n/a",
            max(1, min(5, round(rng.gauss(4.5, 0.6)))),
            foot,
            sust,
            max(1, min(5, round(rng.gauss(3.9, 0.9)))),
            max(1, min(5, round(rng.gauss(3.6, 1.0)))),
            consider,
        ]
        ws.append(row)
    cb = wb.create_sheet("Codebook")
    cb.append(["variable", "description", "scale"])
    for v, desc, scale in [
        ("home_office_m2", "Floor area of the room used as home office", "m²"),
        ("hours_seated_per_day", "Self-reported hours seated on a work day", "hours"),
        ("back_pain_score_0_10", "Lower-back discomfort at end of work day", "0 = none, 10 = worst"),
        ("wtp_usd", "Willingness to pay for a chair meeting all stated needs", "USD; 'n/a' = refused"),
        ("imp_*", "Importance of attribute when choosing a chair", "1 = not important, 5 = critical"),
        ("would_consider_kestrel", "Interest after reading the KESTREL concept description", "Yes / Maybe / No"),
    ]:
        cb.append([v, desc, scale])
    wb.properties.title = "Home-office seating survey 2026"
    wb.properties.created = FIXED_TIME
    wb.save(path)


def write_competitors(path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Benchmark"
    ws.append(
        [
            "model",
            "brand",
            "price_usd",
            "base_diameter_mm",
            "seat_width_mm",
            "weight_kg",
            "max_load_kg",
            "armrests",
            "lumbar",
            "recycled_content_pct",
            "warranty_years",
            "assembly_min",
            "avg_rating",
            "reviews",
        ]
    )
    for c in COMPETITORS:
        ws.append(list(c))
    notes = wb.create_sheet("Notes")
    notes.append(["Competitor benchmark, compiled March 2026 by Product Marketing."])
    notes.append(["Prices are list prices in USD; recycled content as claimed by the brand."])
    notes.append(["All brands and models are fictional (synthetic training data)."])
    wb.properties.title = "Competitor benchmark 2026"
    wb.properties.created = FIXED_TIME
    wb.save(path)


def write_materials(path: Path) -> None:
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shell_Fatigue"
    ws["A1"] = "Seat shell cyclic fatigue — internal test program TP-07"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "Load 1,100 N at 1 Hz; test stops at failure or at 200,000 cycles (runout). Target: 120,000 cycles."
    ws.append([])
    ws.append(
        ["sample_id", "material", "batch", "cycles_to_failure", "failure_mode", "runout", "test_date", "technician"]
    )
    n = 0
    for m_idx, (material, rows) in enumerate(SHELL_FATIGUE.items()):
        for s_idx, (cycles, mode) in enumerate(rows):
            n += 1
            ws.append(
                [
                    f"S-{n:02d}",
                    material,
                    f"B{m_idx + 1}-{s_idx // 3 + 1}",
                    cycles,
                    mode,
                    "Y" if cycles >= 200000 else "N",
                    date(2026, 3, 2 + n),
                    "J. Kowalczyk" if n % 2 else "M. Nowak",
                ]
            )
    props = wb.create_sheet("Material_Properties")
    props.append(
        [
            "material",
            "description",
            "recycled_content_pct",
            "cost_usd_per_kg",
            "co2e_kg_per_kg",
            "density_g_cm3",
            "shell_mass_kg",
        ]
    )
    for m in MATERIALS:
        props.append(list(m))
    foam = wb.create_sheet("Foam")
    foam.append(["option", "density_kg_m3", "compression_set_pct", "recycled_content_pct", "cost_usd_per_seat"])
    for f in FOAM:
        foam.append(list(f))
    wb.properties.title = "Seat shell materials test results"
    wb.properties.created = FIXED_TIME
    wb.save(path)


def write_quotes(path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotes"
    ws.append(
        [
            "part_no",
            "part",
            "supplier",
            "country",
            "option",
            "replaces",
            "qty_per_chair",
            "mass_kg_each",
            "recycled_content_pct",
            "unit_price_usd_1k",
            "unit_price_usd_5k",
            "unit_price_usd_10k",
            "tooling_usd",
            "lead_time_weeks",
            "quote_date",
        ]
    )
    for q in QUOTES:
        p5 = q[9]
        ws.append(
            [
                q[0],
                q[1],
                q[2],
                q[3],
                q[4],
                q[5] or None,
                q[6],
                q[7],
                q[8],
                round(p5 * 1.09, 2),
                p5,
                round(p5 * 0.955, 2),
                q[10],
                q[11],
                date(2026, 7, 10),
            ]
        )
    readme = wb.create_sheet("Read_me")
    for line in [
        "Supplier quotes collected by Sourcing, July 2026. Planning basis: 5,000 units per year (unit_price_usd_5k).",
        "option = baseline is the P2 configuration. Options A, B, C are the armrest fixes; alt = alternative sources.",
        "replaces = part number(s) that the row replaces when the option/alternative is chosen (';' separated).",
        "Landed unit cost = sum(qty_per_chair x unit price) including labour (KS-900) and freight (KS-910).",
        "Recycled content is by weight and excludes packaging (KS-180).",
    ]:
        readme.append([line])
    wb.properties.title = "Supplier quotes July 2026"
    wb.properties.created = FIXED_TIME
    wb.save(path)


def write_deck(path: Path, facts: dict) -> None:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt

    c = facts["configs"]
    prs = Presentation()
    prs.core_properties.title = "KESTREL P2 Design Review"
    prs.core_properties.created = FIXED_TIME
    prs.core_properties.modified = FIXED_TIME
    prs.core_properties.last_modified_by = "Aldermoor"
    prs.core_properties.revision = 1

    def bullets(title, items, notes=None):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        tf = s.placeholders[1].text_frame
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            level = 1 if item.startswith("  ") else 0
            p.text = item.strip()
            p.level = level
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def table_slide(title, header, rows, notes=None):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = title
        shape = s.shapes.add_table(
            len(rows) + 1, len(header), Inches(0.4), Inches(1.5), Inches(9.2), Inches(0.4) * (len(rows) + 1)
        )
        for i, h in enumerate(header):
            shape.table.cell(0, i).text = h
        for r, row in enumerate(rows, start=1):
            for i, v in enumerate(row):
                shape.table.cell(r, i).text = str(v)
                shape.table.cell(r, i).text_frame.paragraphs[0].runs[0].font.size = Pt(12)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "KESTREL P2 Design Review"
    s.placeholders[1].text = "27 August 2026 · Product, Engineering, Sourcing, Marketing, Finance"
    bullets(
        "Agenda",
        [
            "P2 results against targets",
            "Armrest bracket failure (T5)",
            "Options and costs",
            "Assembly time",
            "Customer voice",
            "Decision needed",
        ],
    )
    rec = c["baseline_P2"]["recycled_pct"]
    table_slide(
        "P2 against targets",
        ["Metric", "Target", "P2 result", "Status"],
        [
            ("Base diameter", "≤ 600 mm", "592 mm", "OK"),
            ("Seat width", "460–490 mm", "475 mm", "OK"),
            ("Mass", "—", "13.2 kg", "—"),
            ("Carton volume", "≤ 0.12 m³", "0.118 m³", "OK"),
            ("Shell fatigue (T2)", "120,000 cycles", "120,000, no failure", "OK"),
            ("Armrest fatigue (T5)", "60,000 cycles", "38,500 / 41,200", "FAIL"),
            ("Assembly time (T9)", "≤ 10 min", "11.6 min mean", "FAIL"),
            ("Recycled content (BOM estimate)", "≥ 50%", f"{round(rec)}%", "MISS"),
            ("Unit cost at 5k (baseline)", "≤ USD 120", f"USD {c['baseline_P2']['unit_cost_usd']:.2f}", "OK"),
        ],
        notes="Recycled content and unit cost come from the Sourcing quote workbook, July 2026.",
    )
    bullets(
        "Armrest bracket failure (T5)",
        [
            "Zinc die-cast bracket KS-204 cracked at 38,500 and 41,200 cycles (target 60,000)",
            "Crack starts at the R0.5 mm inner radius next to the mounting boss",
            "Sectioning found gas porosity up to 0.4 mm in the crack origin",
            "  FEA peak stress 212 MPa at the radius under the TP-12 load",
        ],
        notes="Hypotheses from TR-2026-031: H1 sharp radius, H2 casting porosity, H3 bolt preload loss.",
    )
    table_slide(
        "Options for the armrest fix",
        ["Option", "Description", "Unit cost delta", "Tooling", "Timeline"],
        [
            (
                "A",
                "Zinc, R2.0 radius + rib",
                f"+USD {c['option_A']['unit_cost_usd'] - c['baseline_P2']['unit_cost_usd']:.2f}",
                "USD 4,800",
                "+3 weeks",
            ),
            (
                "B",
                "Stamped steel bracket",
                f"+USD {c['option_B']['unit_cost_usd'] - c['baseline_P2']['unit_cost_usd']:.2f}",
                "USD 11,500",
                "+5 weeks",
            ),
            (
                "C",
                "Flip-up armrest assembly",
                f"+USD {c['option_C']['unit_cost_usd'] - c['baseline_P2']['unit_cost_usd']:.2f}",
                "USD 26,000",
                "+8 weeks",
            ),
        ],
        notes="Unit cost deltas are per chair at 5,000 units and include both armrests.",
    )
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Assembly time by tester (minutes)"
    cd = CategoryChartData()
    cd.categories = [t for t, _ in ASSEMBLY_TIMES]
    cd.add_series("Assembly time (min)", [v for _, v in ASSEMBLY_TIMES])
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.7), Inches(1.5), Inches(8.5), Inches(5), cd)
    s.notes_slide.notes_text_frame.text = (
        "Target is 10 minutes. Testers 1 and 2 used the printed guide; the backrest-to-mechanism step took longest "
        "for everyone. Captive screws on the backrest are estimated to save about 2 minutes."
    )
    bullets(
        "Customer voice",
        [
            "“I want armrests that fold away when I am typing, then come back when I read.” (P08)",
            "“It is a great chair, it is just enormous. The armrests hit the desk so I cannot pull in.” (P05)",
            "“Tell me the percentage of recycled plastic and I will believe you.” (P09)",
        ],
    )
    bullets(
        "Decision needed",
        [
            "Select armrest option A, B or C for P3",
            "Close the recycled-content gap (EcoLine mechanism?)",
            "Approve captive-screw backrest to cut assembly time",
            "Keep landed unit cost ≤ USD 120 at 5,000 units",
        ],
        notes="Finance will not approve a configuration above USD 120 landed cost without a price change.",
    )
    prs.save(path)


def _pdf(path: Path, title: str, story_fn) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 10 * mm, FOOTER)
        canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def table(rows, widths=None):
        t = Table([[Paragraph(str(c), styles["BodyText"]) for c in r] for r in rows], colWidths=widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return t

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author="Aldermoor Furniture Co.",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    doc.build(story_fn(styles, Paragraph, Spacer, table), onFirstPage=footer, onLaterPages=footer)


def write_test_report(path: Path) -> None:
    from reportlab.platypus import PageBreak

    def story(st, P, S, table):
        return [
            P("Test Report TR-2026-031 — KESTREL Prototype P2", st["Title"]),
            P("Aldermoor Test Lab, Gdańsk · Issued 12 August 2026 · Engineer: Tomasz Wierzbicki", st["BodyText"]),
            S(1, 8),
            P("1. Summary", st["Heading2"]),
            P(
                "Six P2 prototypes were built with an rPP-50 seat shell, a recycled-aluminium base and zinc die-cast "
                "armrest brackets (part KS-204). Nine tests were run against the internal targets. Seven tests passed "
                "and two failed: armrest cyclic fatigue (T5) and assembly time (T9).",
                st["BodyText"],
            ),
            P("2. Results", st["Heading2"]),
            table(
                [["ID", "Test", "Method", "Target", "Result", "Status"]] + [list(t) for t in P2_TESTS],
                [12 * 3.0, 90, 62, 95, 140, 50],
            ),
            PageBreak(),
            P("3. Failure analysis — T5 armrest cyclic", st["Heading2"]),
            P(
                "Unit 2 failed at 38,500 cycles and unit 4 at 41,200 cycles; the remaining unit reached 60,000 cycles "
                "without failure. In both failures a fatigue crack initiated at the R0.5 mm inner radius of bracket "
                "KS-204, next to the rear mounting boss.",
                st["BodyText"],
            ),
            P(
                "Sectioning of unit 2 showed gas porosity up to 0.4 mm at the crack origin. A linear FEA model of the "
                "TP-12 load case gives a peak stress of 212 MPa at the radius.",
                st["BodyText"],
            ),
            P(
                "Hypotheses: H1 — the sharp R0.5 mm radius concentrates stress; H2 — casting porosity reduces fatigue "
                "strength; H3 — loss of bolt preload lets the bracket rock. H3 is considered unlikely because the "
                "bolt torque was still 92% of nominal after the test.",
                st["BodyText"],
            ),
            P("4. Measurements", st["Heading2"]),
            table(
                [
                    ["Measure", "Value"],
                    ["Base diameter", "592 mm"],
                    ["Seat width", "475 mm"],
                    ["Mass (without packaging)", "13.2 kg"],
                    ["Carton volume", "0.118 m³"],
                    ["Seat height range", "420–530 mm"],
                ],
                [200, 200],
            ),
            P("5. Assembly time (T9)", st["Heading2"]),
            P(
                "Five untrained testers assembled the chair from the carton with the included hex key. Times were "
                + ", ".join(f"{v} min" for _, v in ASSEMBLY_TIMES)
                + ". The mean of 11.6 minutes exceeds the 10-minute target. Mounting the backrest to the mechanism "
                "was the slowest step for all testers.",
                st["BodyText"],
            ),
            P("6. Recommendations", st["Heading2"]),
            P(
                "Increase the inner radius of the armrest bracket and eliminate porosity, or change the bracket "
                "process. Candidate fixes are option A (zinc, R2.0 radius plus rib), option B (stamped steel) and "
                "option C (flip-up armrest assembly). Costing is provided by Sourcing. Whichever option is chosen, "
                "T5 must be repeated on P3 with at least three units.",
                st["BodyText"],
            ),
            P("Pre-fit captive screws on the backrest to reduce assembly time, then repeat T9.", st["BodyText"]),
        ]

    _pdf(path, "Test Report TR-2026-031 — KESTREL Prototype P2", story)


def write_market_brief(path: Path) -> None:
    from reportlab.platypus import PageBreak

    def story(st, P, S, table):
        return [
            P("Home-Office Seating — Market Brief 2026", st["Title"]),
            P("Aldermoor Market Intelligence · January 2026 · Internal estimates", st["BodyText"]),
            S(1, 8),
            P("Key takeaways", st["Heading2"]),
            P(
                "The home-office seating market is growing fastest in Asia-Pacific. Online sales dominate, and "
                "returns are driven by comfort and size. The USD 200–399 band is the largest mid-market band.",
                st["BodyText"],
            ),
            P("1. Market size by region (retail value, 2025)", st["Heading2"]),
            table(
                [
                    ["Region", "Market size 2025 (USD bn)", "CAGR 2026–2030"],
                    ["North America", "2.9", "4.8%"],
                    ["Europe", "2.1", "5.6%"],
                    ["Asia-Pacific", "1.6", "7.9%"],
                ],
                [160, 150, 120],
            ),
            P("2. Unit share by price band", st["Heading2"]),
            table(
                [
                    ["Price band", "Share of units"],
                    ["Under USD 200", "38%"],
                    ["USD 200–399", "34%"],
                    ["USD 400–799", "21%"],
                    ["USD 800 and above", "7%"],
                ],
                [200, 150],
            ),
            PageBreak(),
            P("3. Channels and returns", st["Heading2"]),
            P(
                "Online channels account for 62% of home-office chair unit sales. The average online return rate "
                "for task chairs is 14%.",
                st["BodyText"],
            ),
            table(
                [
                    ["Return reason", "Share of returns"],
                    ["Uncomfortable", "31%"],
                    ["Too big for the space", "23%"],
                    ["Damaged in transit", "18%"],
                    ["Assembly problems", "12%"],
                    ["Other", "16%"],
                ],
                [200, 150],
            ),
            P("4. Consumer trends", st["Heading2"]),
            P(
                "Small-space living: new urban apartments are getting smaller, and a growing share of remote "
                "workers use a bedroom corner or a converted closet as their office.",
                st["BodyText"],
            ),
            P(
                "Sustainability with proof: shoppers respond to specific recycled-content percentages; vague "
                "'eco' claims face growing regulatory scrutiny in the EU.",
                st["BodyText"],
            ),
            P(
                "Assembly as a brand moment: brands that ship chairs in a single box with tool-free or one-tool "
                "assembly report fewer support contacts.",
                st["BodyText"],
            ),
        ]

    _pdf(path, "Home-Office Seating — Market Brief 2026", story)


def write_notes(path: Path) -> None:
    path.write_text(
        "# Design ideas backlog\n\n"
        "Owner: Aiko Tanaka · last updated 2026-08-28\n\n"
        "## Armrests\n\n"
        "- Flip-up armrest that parks flush with the backrest when typing.\n"
        "- Height-adjustable post sharing parts with the fixed version to keep tooling low.\n\n"
        "## Assembly\n\n"
        "- Captive screws pre-fitted on the backrest bracket.\n"
        "- Colour-coded bolts matching a one-page picture guide.\n"
        "- QR code on the carton linking to a 90-second assembly video.\n\n"
        "## Materials\n\n"
        "- Use the EcoLine mechanism if Sourcing confirms the price.\n"
        "- Print the exact recycled-content percentage on the seat underside.\n",
        encoding="utf-8",
    )


def write_readme(root: Path) -> None:
    (root / "README.md").write_text(
        "# KESTREL demo workspace\n\n"
        "A synthetic R&D project for learning the RnD toolset: Aldermoor Furniture Co. is developing **KESTREL**, "
        "a compact ergonomic task chair for small home offices. The prototype P2 has just been tested and the team "
        "must decide how to fix a failed armrest bracket while hitting cost and recycled-content targets.\n\n"
        "All companies, people and figures are fictional.\n\n"
        "| Folder | What is inside |\n|---|---|\n"
        "| `sources/meetings` | Kickoff notes (targets), weekly sync (Word) |\n"
        "| `sources/customers` | 12 interview write-ups (Word), survey with 240 responses (Excel) |\n"
        "| `sources/competitors` | Benchmark of 8 competitor chairs (Excel) |\n"
        "| `sources/engineering` | Shell material fatigue tests (Excel), P2 test report (PDF) |\n"
        "| `sources/suppliers` | Supplier quotes / BOM with options A, B, C (Excel) |\n"
        "| `sources/design` | P2 design review deck (PowerPoint) |\n"
        "| `sources/market` | Market brief (PDF) |\n"
        "| `notes` | Designer's idea backlog (Markdown) |\n"
        "| `outputs` | Where RnD writes reports, decks and spreadsheets |\n\n"
        "Start with `TUTORIAL.md`, or run `/rnd:tutorial` in Claude Code.\n",
        encoding="utf-8",
    )


# (path, doc id, what is inside) — tests check the ids against the real index
TUTORIAL_DOCS = [
    ("sources/meetings/2026-02-09 Kickoff - Project KESTREL.docx", "2026-02-09-kickoff-project-kestrel",
     "Word · product targets table (t1), decisions D1–D3, risks"),
    ("sources/meetings/2026-08-20 Weekly sync.docx", "2026-08-20-weekly-sync",
     "Word · armrest options A/B/C, positions of Finance, Marketing, Engineering, Sourcing"),
    ("sources/customers/Customer interviews Q2 2026.docx", "customer-interviews-q2-2026",
     "Word · 12 interview summaries with quotes, coded pain-point table (t2), synthesis"),
    ("sources/customers/Seating survey 2026 - responses.xlsx", "seating-survey-2026-responses",
     "Excel · 240 survey responses"),
    ("sources/competitors/Competitor benchmark 2026.xlsx", "competitor-benchmark-2026",
     "Excel · 8 competitor chairs: price, base size, weight limit, recycled content"),
    ("sources/engineering/Seat shell materials - test results.xlsx", "seat-shell-materials-test-results",
     "Excel · shell fatigue (24 samples), materials, seat foam options"),
    ("sources/engineering/TR-2026-031 P2 prototype test report.pdf", "tr-2026-031-p2-prototype-test-report",
     "PDF · the 9 P2 tests, armrest failure analysis, assembly observations"),
    ("sources/suppliers/Supplier quotes 2026-07.xlsx", "supplier-quotes-2026-07",
     "Excel · every part with price at 1k/5k/10k units, mass, recycled %, lead time"),
    ("sources/design/P2 design review 2026-08-27.pptx", "p2-design-review-2026-08-27",
     "PowerPoint · P2 vs targets, armrest failure, options and costs, assembly chart"),
    ("sources/market/Home office seating market brief 2026.pdf", "home-office-seating-market-brief-2026",
     "PDF · market size, price bands, sales channels, reasons for returns"),
    ("notes/ideas-backlog.md", "ideas-backlog", "Markdown · the designer's idea backlog"),
]  # fmt: skip


def write_tutorial(path: Path, facts: dict) -> None:
    """TUTORIAL.md with expected answers taken from the same data as the documents."""
    c = facts["configs"]
    t = facts["interview_theme_counts"]
    sm = facts["shell_mean_cycles"]
    smin = facts["shell_min_cycles"]
    spass = facts["shell_samples_passing"]
    n_int = facts["interviews_total"]
    kick = "2026-02-09-kickoff-project-kestrel"

    def fmt(x: float) -> str:
        return f"{x:,.2f}".rstrip("0").rstrip(".")

    def meets(key: str) -> bool:
        return c[key]["unit_cost_usd"] <= UNIT_COST_TARGET and c[key]["recycled_pct"] >= RECYCLED_TARGET

    docs = "\n".join(f"| `{did}` | {what} |" for _p, did, what in TUTORIAL_DOCS)
    target_rows = "\n".join(
        f"| {name} | {value} | `{kick}#t1.r{i + 2}` |" for i, (name, value, _why) in enumerate(TARGETS)
    )
    shell_rows = "\n".join(
        f"| {m} | {fmt(sm[m])} | {smin[m]:,} | {spass[m]} of 6 | {'yes' if sm[m] >= SHELL_TARGET else '**no**'} |"
        for m in sorted(sm, key=lambda k: -sm[k])
    )
    config_keys = [
        ("baseline_P2", "P2 baseline", "standard"),
        ("baseline_P2_eco", "P2 baseline", "EcoLine"),
        ("option_A", "Option A", "standard"),
        ("option_A_eco", "Option A", "EcoLine"),
        ("option_B", "Option B", "standard"),
        ("option_B_eco", "Option B", "EcoLine"),
        ("option_C", "Option C", "standard"),
        ("option_C_eco", "Option C", "EcoLine"),
    ]
    config_rows = "\n".join(
        f"| {label} | {mech} | {c[k]['unit_cost_usd']:.2f} | {c[k]['recycled_pct']:.2f} | "
        f"{'**yes**' if meets(k) else 'no'} |"
        for k, label, mech in config_keys
    )
    both = [label + " + EcoLine" for k, label, mech in config_keys if mech == "EcoLine" and meets(k)]
    hanoi = c["option_C_eco_hanoi_shell"]
    assembly_mean = facts["assembly_mean_min"]

    path.write_text(
        f"""# RnD tutorial — Project KESTREL

Aldermoor Furniture Co. is developing **KESTREL**, a compact ergonomic task chair for small
home offices. Prototype P2 has been tested: the armrest bracket cracked, assembly takes too
long, and the team must choose a fix for P3 while keeping the landed unit cost at or below
USD 120 and recycled content at or above 50%. Everything here is fictional, but the numbers
are consistent across all documents, so you can check every answer RnD gives you.

The 12 lessons take about 60–90 minutes in total. Each one shows a command to type, what
happens behind the scenes, the answer you should get, and how to check it yourself.

## 0. Before you start

1. **Open Claude Code in this folder** (`cd` into it, then run `claude`) and accept the
   "trust this folder" prompt. Until you do, Claude Code ignores this folder's settings.
2. **Check the model.** This folder's default is Sonnet (`.claude/settings.json`). If you
   pick Opus with `/model`, the `/rnd:*` commands still run their steps on Haiku and
   Sonnet (only `/rnd:decide` uses Opus, for the final reasoning). What Opus changes is
   the cost of your *free-form* questions, which the session model answers.
3. **Keep `/cost` handy**: run it after a lesson to see what the lesson cost.
4. **Where things go:**

| Folder | What is in it |
|---|---|
| `sources/`, `notes/` | the project documents (read-only for RnD) |
| `outputs/` | what RnD writes for you: answers to share, reports, decks, spreadsheets |
| `.rnd/packs/` | evidence packs and `/rnd:ask` answers (Markdown, every fact cited) |
| `.rnd/calcs/` | every SQL result as `N.json` — cited as `[@calc:N]` |

5. **How to read a citation.** Every fact carries one. Show the source behind any of them
   with `/rnd:show <ref>` (Lesson 2).

| Citation | Points to |
|---|---|
| `[@{kick}#t1.r3]` | Word document, table 1, row 3 |
| `[@{kick}#p14]` | Word document, 14th paragraph |
| `[@tr-2026-031-p2-prototype-test-report#page2]` | PDF, page 2 |
| `[@p2-design-review-2026-08-27#s5.t1]` | PowerPoint, slide 5, its table |
| `[@supplier-quotes-2026-07#Quotes!A8:O8]` | Excel, sheet "Quotes", row 8 |
| `[@calc:5]` | the SQL query and exact result saved in `.rnd/calcs/5.json` |

### The documents

| Doc id | What is inside |
|---|---|
{docs}

---

## Lesson 1 — a cited answer (Haiku)

```
/rnd:ask What are the product targets for KESTREL?
```

**Behind the scenes.** The command runs in its own context on the `librarian` agent
(Haiku). It searches with several phrasings, reads the kickoff notes' target table, writes
`.rnd/packs/answer-<slug>.md`, and the verifier checks every citation and figure in it.

**You should get** these 11 targets, each cited to its own table row:

| Target | Value | Citation |
|---|---|---|
{target_rows}

**Check it yourself.** Every bullet should cite a single row (`#t1.r3`), not the whole
table (`#t1`). The answer file in `.rnd/packs/` is plain Markdown; open it in any editor.

## Lesson 2 — check a source

```
/rnd:show {kick}#t1.r3
```

**You should get** the verbatim row — `Target: Unit cost (landed, incl. packaging) | Value:
≤ USD 120 | Rationale: Keeps gross margin above 60% at USD 349 after channel fees.` — plus
where to find it: `sources/meetings/2026-02-09 Kickoff - Project KESTREL.docx` → table 1,
row 3. `/rnd:show calc:N` shows the SQL and the exact rows of a calculation the same way.

## Lesson 3 — counting belongs to SQL

```
/rnd:ask How many interviewees said their chair is too bulky, and what did they say?
```

**You should get** **{t["footprint"]} of {n_int}** participants (P01, P03, P05, P06, P07, P09,
P11, P12), counted with SQL over the coded pain-point table in the interview document and
cited as `[@calc:N]`, plus verbatim quotes such as P01's “My chair is wider than the room is
deep…”, P05's “It is a great chair, it is just enormous…” and P07's “Anything with a huge
star base…”. A good answer also says that four of the eight (P03, P06, P09, P11) are coded
"too bulky" but are only quoted about other topics.

**Why it matters.** The count comes from a query, not from the model reading paragraphs;
`/rnd:show calc:N` shows the query.

## Lesson 4 — exact numbers (Sonnet + SQL)

```
/rnd:analyze Mean and minimum cycles to failure per seat shell material; which pass the 120,000-cycle target?
```

**Behind the scenes.** Runs on the `analyst` agent (Sonnet). It lists the SQL tables,
probes the Shell_Fatigue sheet, computes everything in SQL and writes
`outputs/figures-<slug>.md`.

**You should get:**

| Material | Mean cycles | Minimum | Samples ≥ 120,000 | Mean passes |
|---|---|---|---|---|
{shell_rows}

rPP-100 is the only material below target. The file cites `[@calc:N]` for every figure;
`.rnd/calcs/N.json` holds the SQL and the full-precision result. Four PA11-GF bio samples
stopped at the 200,000-cycle runout, so its real mean is higher — a careful answer says so.

## Lesson 5 — a what-if across documents, exported to Excel

```
/rnd:analyze Landed unit cost and recycled content for the P2 baseline and each armrest option, with and without the EcoLine mechanism --xlsx
```

**You should get** (USD per chair at the 5,000-unit price; recycled % by weight, packaging
excluded):

| Armrest | Mechanism | Unit cost (USD) | Recycled % | Meets both targets |
|---|---|---|---|---|
{config_rows}

Without EcoLine nothing reaches 50% recycled content. With EcoLine, **{len(both)}
configurations meet both targets**: {", ".join(both)}. Option C is over USD 120 either way.
The P2 baseline + EcoLine passes on cost and recycled content, but it keeps the bracket
that cracked — that is why Lesson 9 compares A and B.

**Check it yourself.** Open `outputs/figures-<slug>.xlsx`: typed numbers, a native chart,
and a Provenance sheet with the SQL. The design-review deck rounds the baseline recycled
content to {round(c["baseline_P2"]["recycled_pct"])}%; the exact value is {c["baseline_P2"]["recycled_pct"]:.2f}%.

**Try next:** `/rnd:analyze Option C with EcoLine and the Hanoi seat shell` — USD
{hanoi["unit_cost_usd"]:.2f}, {hanoi["recycled_pct"]:.2f}%: the cheaper shell source still
leaves C over the limit.

## Lesson 6 — grounded brainstorming

```
/rnd:brainstorm How to cut assembly time below 10 minutes
```

**Behind the scenes.** The librarian (Haiku) builds an evidence pack; the `ideator`
(Sonnet) generates 12–20 ideas, links each to its evidence, scores them and writes
`outputs/brainstorm-<slug>.md`. The command stays on Sonnet from start to finish.

**You should get** ideas such as captive screws on the backrest, colour-coded bolts, a
keyed backrest or a QR-code assembly video. Each should cite its motivating evidence: the
P2 mean of {assembly_mean} minutes (range 9.1–14.2), the backrest-to-mechanism step being
the slowest for every tester, P06's “It took me forty…” and P03's “…put the back on the
wrong way, twice.” Assumptions are labelled `Assumption:` and the scoring table is marked
"(judgement)".

## Lesson 7 — a verified Word report

```
/rnd:report P2 test status for the steering committee
```

**Behind the scenes.** Librarians (Haiku) gather 2–4 evidence packs in parallel while
the analyst (Sonnet) computes the figures; the `writer` (Sonnet) drafts
`outputs/<slug>.md`, verifies it and renders the `.docx`. Because the audience is outside
the project team, the `auditor` (Haiku) then checks that every source really says what
the report claims, and the writer fixes whatever it finds. Expect about 10 minutes.

**You should get** a Word file with a summary, the 9 tests (7 passed; T5 armrest fatigue
— cracks at 38,500 and 41,200 cycles against 60,000 — and T9 assembly time — 11.6 min
mean against 10 — failed), status against targets (5 of 8 OK, 2 FAIL, recycled content
MISS), cost and recycled-content status, a numbered Sources list, and the footer
"Citations verified (PASS)".

**See the precision gate work.** Ask Claude: `In the report Markdown, change 38,500 to
39,000`. The verifier reports a `figure-mismatch` immediately and `render` refuses to
produce a new .docx until it is fixed. If you edit the Markdown in your own editor, the
check is not automatic — run `/rnd:verify outputs/<slug>.md`.

## Lesson 8 — check a document before sharing

```
/rnd:verify --deep
```

The deterministic verifier guarantees refs, quotes and figures (no model involved).
`--deep` adds the `auditor` (Haiku), which flags claims the source does not really
support — a count that is off ("six of eight" when the rows show five), a target presented
as a result, "approved" where the source says "evaluate".

## Lesson 9 — the one place Opus is used

```
/rnd:decide Which armrest option should go into P3?
```

**Behind the scenes.** The librarian (Haiku) builds the evidence pack and the analyst
(Sonnet) computes the option figures in parallel; only then does the `strategist` (Opus)
reason over that small pack. The auditor (Haiku) checks the memo and the strategist fixes
what it flags. Expect about 8 minutes.

**A good memo** (`outputs/decision-<slug>.md`):
- rules out **Option C** (flip-up): customers asked for it ({t["armrests"]} of 12 raised
  armrests) but it costs USD {c["option_C"]["unit_cost_usd"]:.2f} — USD {c["option_C_eco"]["unit_cost_usd"]:.2f}
  with EcoLine — above the USD 120 limit, with the highest tooling cost (USD 26,000) and the
  longest delay (+8 weeks);
- says **EcoLine is needed** whichever option wins: no configuration reaches 50% recycled
  content without it;
- compares **A + EcoLine** (USD {c["option_A_eco"]["unit_cost_usd"]:.2f}, {c["option_A_eco"]["recycled_pct"]:.2f}%) and **B + EcoLine** (USD
  {c["option_B_eco"]["unit_cost_usd"]:.2f}, {c["option_B_eco"]["recycled_pct"]:.2f}%): A is cheaper but keeps the zinc casting whose porosity is a
  suspected crack cause (hypothesis H2); B removes both suspected causes, as Engineering
  said in the weekly sync;
- recommends **B + EcoLine with medium confidence**, and lists the gaps: no fatigue data
  for any fix yet, B leaves only USD {UNIT_COST_TARGET - c["option_B_eco"]["unit_cost_usd"]:.2f} under the cost limit, and the supplier lead
  times and the design review's timeline (+3 / +5 / +8 weeks) are not reconciled.

It should quote kickoff decision D2 exactly — "Evaluate flip-up armrests as an option" —
not as an approval of Option C.

## Lesson 10 — a deck with native charts

```
/rnd:deck P3 armrest decision for the design review
```

**You should get** `outputs/<slug>-deck.pptx`: takeaway titles ("Option B + EcoLine is
the only fix that removes both crack causes within budget", not "Options"), a native
chart built from a calc (click it → "Edit data" in PowerPoint), speaker notes, and Sources
slides. It reuses the evidence from Lesson 9 if you ran it.

## Lesson 11 — evidence from the web

```
/rnd:capture <URL of a public page about office-chair ergonomics>
```

The `scout` (Haiku) saves the page's text verbatim in `sources/web/` with its URL and
fetch date and indexes it. From then on it can be cited like any other document.
Without a URL, `/rnd:capture <topic>` searches the web and captures up to 5 primary
sources.

## Lesson 12 — your own questions

Ask anything about the project. Questions that name the thing you want get the best
answers:

| Vague | Better |
|---|---|
| what is the last two of the seat? | `/rnd:ask What are the last two seat foam options and what do they cost?` |
| is the chair ok? | `/rnd:ask Which P2 tests failed, and by how much?` |
| numbers for the survey | `/rnd:analyze Average willingness to pay by region --xlsx` |

When a question is ambiguous, `/rnd:ask` answers the most likely reading, says which one
it chose (`Assumption: …`) and lists the other readings under Gaps, so you can re-ask.

---

## What to expect in time and cost

| Lesson | Models | Typical time |
|---|---|---|
| 1–3 `/rnd:ask`, `/rnd:show` | Haiku | under 1–2 min |
| 4–5 `/rnd:analyze` | Sonnet | 2–4 min |
| 6 `/rnd:brainstorm` | Haiku → Sonnet | about 5 min |
| 7 `/rnd:report` (with audit) | Haiku → Sonnet → Haiku | about 10 min |
| 9 `/rnd:decide` (with audit) | Haiku + Sonnet → Opus → Haiku | about 8 min |

List prices per million tokens (input/output): Haiku $1/$5, Sonnet $2/$10, Opus $4/$20.
Run `/cost` after a lesson for the real figure.

## If something looks wrong

| You see | What it means / what to do |
|---|---|
| A figure different from this tutorial | A bug — please report it with the answer file from `.rnd/packs/` or `outputs/`. |
| `FAIL … figure-mismatch` | A number is not in the cited source at the precision written. Claude fixes it; if you edited by hand, fix the number or cite the right row. |
| `uncited-figure` | A sentence states a number without a citation. |
| `bad-quote` | A quoted phrase is not word-for-word in the source. |
| `WARN … broad-ref` | The citation points at a whole table or long range; cite the row. |
| "Read was denied for a .pdf/.docx" | On purpose: RnD reads the exact part instead of the whole file. |
| An agent "stalled" | Usually the computer slept. Ask Claude to run that step again. |
| The RnD tools are missing | Run `/rnd:setup`; if it still fails, `/mcp` → reconnect `plugin:rnd:rnd`. |

## What to take away

- Start with a `/rnd:*` command instead of free chat: each one picks the cheapest model
  that can do the job, and checks the result.
- Never paste or open whole documents; RnD reads the part that matters, exactly.
- Every number traces to a document row or a calc — check any of them with `/rnd:show`.
- For your own project: make a folder, put documents in `sources/`, open Claude Code
  there and run `/rnd:setup`. See the user guide for more.
""",
        encoding="utf-8",
    )


def build(out: Path) -> dict:
    facts = golden_facts()
    for sub in (
        "sources/meetings",
        "sources/customers",
        "sources/competitors",
        "sources/engineering",
        "sources/suppliers",
        "sources/design",
        "sources/market",
        "notes",
        "outputs",
    ):
        (out / sub).mkdir(parents=True, exist_ok=True)
    write_kickoff(out / "sources/meetings/2026-02-09 Kickoff - Project KESTREL.docx")
    write_sync(out / "sources/meetings/2026-08-20 Weekly sync.docx", facts)
    write_interviews(out / "sources/customers/Customer interviews Q2 2026.docx")
    write_survey(out / "sources/customers/Seating survey 2026 - responses.xlsx")
    write_competitors(out / "sources/competitors/Competitor benchmark 2026.xlsx")
    write_materials(out / "sources/engineering/Seat shell materials - test results.xlsx")
    write_test_report(out / "sources/engineering/TR-2026-031 P2 prototype test report.pdf")
    write_quotes(out / "sources/suppliers/Supplier quotes 2026-07.xlsx")
    write_deck(out / "sources/design/P2 design review 2026-08-27.pptx", facts)
    write_market_brief(out / "sources/market/Home office seating market brief 2026.pdf")
    write_notes(out / "notes/ideas-backlog.md")
    write_readme(out)
    write_tutorial(out.parent / "TUTORIAL.md", facts)
    (out / "outputs" / ".gitkeep").write_text("")
    return facts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    facts = build(args.out)
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(json.dumps(facts, indent=2) + "\n")
    print(f"demo written to {args.out}")
    print(json.dumps(facts["configs"], indent=1))


if __name__ == "__main__":
    main()
