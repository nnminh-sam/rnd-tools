"""DocModel -> PDF (reportlab). Uses a system Unicode font when one exists so that
Vietnamese and other accented text renders; charts are native vector graphics."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .model import Block, DocModel, Run, chart_data, describe_sources, runs_text

_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
]


def _fonts() -> tuple[str, str]:
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular, bold in _FONT_CANDIDATES:
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont("RnDSans", regular))
                pdfmetrics.registerFont(TTFont("RnDSans-Bold", bold))
                addMapping("RnDSans", 0, 0, "RnDSans")
                addMapping("RnDSans", 1, 0, "RnDSans-Bold")
                addMapping("RnDSans", 0, 1, "RnDSans")
                addMapping("RnDSans", 1, 1, "RnDSans-Bold")
                return "RnDSans", "RnDSans-Bold"
            except Exception:  # pragma: no cover - unreadable font file
                continue
    return "Helvetica", "Helvetica-Bold"


def _markup(runs: list[Run]) -> str:
    out = []
    for r in runs:
        if r.cites:
            out.append(f"<super><font size=7 color='#445588'>[{','.join(map(str, r.cites))}]</font></super>")
            continue
        t = escape(r.text).replace("\n", "<br/>")
        if r.code:
            t = f"<font face='Courier'>{t}</font>"
        if r.bold:
            t = f"<b>{t}</b>"
        if r.italic:
            t = f"<i>{t}</i>"
        if r.link:
            t = f"<link href='{escape(r.link)}' color='#1f4e9a'>{t}</link>"
        out.append(t)
    return "".join(out)


def _chart(ws, b: Block, width: float, font: str = "Helvetica"):
    from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors

    cats, series, title = chart_data(ws, b.spec)
    palette = [colors.HexColor(c) for c in ("#2f5d8a", "#e0873a", "#5a9e6f", "#b04a5a", "#7d6bb0")]
    h = 220
    d = Drawing(width, h)
    kind = b.spec.get("type", "column")
    if kind == "pie":
        c = Pie()
        c.x, c.y, c.width, c.height = width / 2 - 80, 20, 160, 160
        c.data = series[0][1]
        c.labels = cats
        for i in range(len(cats)):
            c.slices[i].fillColor = palette[i % len(palette)]
    else:
        c = {"bar": HorizontalBarChart, "line": HorizontalLineChart}.get(kind, VerticalBarChart)()
        c.x, c.y, c.width, c.height = 50, 35, width - 70, h - 70
        c.data = [vals for _, vals in series]
        c.categoryAxis.categoryNames = cats
        c.categoryAxis.labels.fontSize = 7
        c.categoryAxis.labels.fontName = font
        c.valueAxis.labels.fontName = font
        c.valueAxis.labels.fontSize = 7
        c.valueAxis.valueMin = 0
        for i in range(len(series)):
            if kind == "line":
                c.lines[i].strokeColor = palette[i % len(palette)]
            else:
                c.bars[i].fillColor = palette[i % len(palette)]
    d.add(c)
    if title:
        d.add(String(width / 2, h - 14, title, textAnchor="middle", fontSize=10, fontName=font))
    if len(series) > 1 and kind != "pie":
        leg = Legend()
        leg.x, leg.y, leg.fontName, leg.fontSize = width - 150, h - 22, font, 7
        leg.alignment = "right"
        leg.colorNamePairs = [(palette[i % len(palette)], name) for i, (name, _) in enumerate(series)]
        d.add(leg)
    return d, cats, series


def render(ws, model: DocModel, out: Path, template: Path | None = None, footer_note: str = "") -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        ListFlowable,
        ListItem,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    regular, bold = _fonts()
    ss = getSampleStyleSheet()
    for st in ss.byName.values():
        if hasattr(st, "fontName"):
            st.fontName = bold if "Bold" in st.fontName or st.name.startswith(("Heading", "Title")) else regular
    body = ss["BodyText"]
    body.spaceAfter = 5
    quote = ParagraphStyle("Quote", parent=body, leftIndent=14, textColor=colors.HexColor("#444444"), fontName=regular)
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=10)
    story = []
    width = A4[0] - 36 * mm

    if model.meta.get("title"):
        story.append(Paragraph(escape(model.meta["title"]), ss["Title"]))
        sub = " · ".join(v for v in (model.meta.get("subtitle"), model.meta.get("author"), model.meta.get("date")) if v)
        if sub:
            story.append(Paragraph(escape(sub), ss["Italic"]))
        story.append(Spacer(1, 8))

    def table(header, rows):
        data = [[Paragraph(_markup(c), small) for c in r] for r in ([header] if header else []) + rows]
        if not data:
            return None
        t = Table(data, repeatRows=1 if header else 0, hAlign="LEFT")
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f0")))
        t.setStyle(TableStyle(style))
        return t

    fig = 0
    for b in model.blocks:
        if b.kind == "heading":
            story.append(Paragraph(_markup(b.runs), ss[f"Heading{min(b.level, 4)}"]))
        elif b.kind == "para":
            story.append(Paragraph(_markup(b.runs), body))
        elif b.kind == "quote":
            story.append(Paragraph(_markup(b.runs), quote))
        elif b.kind == "list":
            items = [ListItem(Paragraph(_markup(runs), body), leftIndent=12 + 12 * depth) for depth, runs in b.items]
            story.append(
                ListFlowable(items, bulletType="1" if b.ordered else "bullet", start="1" if b.ordered else None)
            )
        elif b.kind == "table":
            t = table(b.header, b.rows)
            if t is not None:
                story += [t, Spacer(1, 6)]
        elif b.kind == "code":
            story.append(Preformatted(b.text, ss["Code"]))
        elif b.kind == "image":
            path = ws.abspath(b.text)
            if path.exists():
                img = Image(str(path))
                ratio = min(1.0, width / img.drawWidth)
                img.drawWidth, img.drawHeight = img.drawWidth * ratio, img.drawHeight * ratio
                story.append(img)
        elif b.kind == "chart":
            fig += 1
            drawing, cats, series = _chart(ws, b, width, regular)
            story.append(drawing)
            header = [[Run(b.spec.get("x") or "category")]] + [[Run(n)] for n, _ in series]
            rows = [[[Run(c)]] + [[Run(_fmt(v[i]))] for _, v in series] for i, c in enumerate(cats)]
            story.append(table(header, rows))
            src = f" (source: calc:{b.spec['calc']})" if "calc" in b.spec else ""
            story.append(Paragraph(escape(f"Figure {fig}: {b.spec.get('title') or 'Chart data'}{src}"), ss["Italic"]))

    if model.sources:
        story.append(Paragraph("Sources", ss["Heading1"]))
        for s, text in zip(model.sources, describe_sources(ws, model.sources)):
            q = f" — <i>“{escape(s.quote)}”</i>" if s.quote else ""
            story.append(Paragraph(f"<b>[{s.number}]</b> {escape(text)}{q}", small))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.drawString(18 * mm, 10 * mm, footer_note[:150])
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        title=model.title,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out


def _fmt(v: float) -> str:
    from ..util import display_number

    return display_number(v)


__all__ = ["render", "runs_text"]
