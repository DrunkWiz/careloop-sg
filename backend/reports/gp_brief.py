"""One-page GP brief, as a PDF. Owner: Nathan.

Input is the dict from GET /senior/{id}/brief.json (backend/api/app.py: brief_data). Every line on the
page comes from that dict, which comes from the decision log; nothing is invented here, and no model
is called. The page is always one A4 sheet: content that doesn't fit is shrunk, and long lists are cut
to their most recent entries with a count of what was left out.

    python -m backend.reports.gp_brief brief.json brief.pdf
"""
from __future__ import annotations

import io
import json
import sys
from datetime import date
from statistics import mean
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import KeepInFrame, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Chinese in the senior's own words. A CID font is not embedded, so the PDF stays small; every
# common viewer (Acrobat, Chrome, Edge, macOS Preview) ships it.
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5f6660")
RULE = colors.HexColor("#d9ddd6")
ACCENT = colors.HexColor("#0b6e4f")
WARN = colors.HexColor("#8a5a00")
ALERT = colors.HexColor("#b3261e")

RUNG = {"3": ("Noted", WARN), "4": ("Handed over", WARN), "R": ("Red flag", ALERT)}
SYMPTOM = {
    "chest_pain": "chest pain", "face_droop": "face drooping", "slurred_speech": "slurred speech",
    "one_sided_weakness": "weakness on one side", "fainting": "fainting", "dizziness": "dizziness",
    "headache": "headache", "breathless": "breathlessness",
}
DANGER = {"chest_pain", "face_droop", "slurred_speech", "one_sided_weakness", "fainting"}
MAX_EVENTS = 8
MAX_WORDS = 5

W, H = A4
MARGIN = 16 * mm
BODY_W = W - 2 * MARGIN


def _style(name: str, size: float = 9, color=INK, bold: bool = False, leading: Optional[float] = None, space: float = 0):
    return ParagraphStyle(name, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, textColor=color,
                          leading=leading or size * 1.3, spaceAfter=space, alignment=TA_LEFT)


S_TITLE = _style("title", 16, bold=True, leading=19)
S_SUB = _style("sub", 9, MUTED)
S_H = _style("h", 10, ACCENT, bold=True, space=3)
S_BODY = _style("body", 9)
S_SMALL = _style("small", 7.5, MUTED)
S_CELL = _style("cell", 8.5)
S_CELL_MUTED = _style("cellm", 7.5, MUTED)


def _has_cjk(s: str) -> bool:
    return any("⺀" <= ch <= "鿿" or "豈" <= ch <= "﫿" or "＀" <= ch <= "￯" for ch in s)


def _text(s: str) -> str:
    """Escape for a Paragraph, switching to the CJK font where needed."""
    s = escape(s)
    return f'<font name="STSong-Light">{s}</font>' if _has_cjk(s) else s


def _d(iso: str) -> str:
    t = date.fromisoformat(iso[:10])
    return f"{t.day} {t:%b}"


def _dy(iso: str) -> str:
    t = date.fromisoformat(iso[:10])
    return f"{t.day} {t:%b %Y}"


def _pick(items: list[dict], limit: int, must) -> list[dict]:
    """Most recent first, cut to `limit`, but never cutting an item `must` keeps (a red flag, a danger symptom)."""
    newest = sorted(items, key=lambda i: i["date"], reverse=True)
    kept = [i for i in newest if must(i)]
    for i in newest:
        if len(kept) >= limit:
            break
        if i not in kept:
            kept.append(i)
    return sorted(kept, key=lambda i: i["date"], reverse=True)


def _recent_avg(bp_daily: list[dict], n: int = 7) -> Optional[tuple[float, float, int]]:
    last = [p for p in bp_daily[-n:] if p.get("systolic") is not None and p.get("diastolic") is not None]
    if not last:
        return None
    return mean(p["systolic"] for p in last), mean(p["diastolic"] for p in last), len(last)


def _chart(data: dict, width: float, height: float = 64 * mm) -> Drawing:
    """90 days of daily BP against the senior's own baseline, with rung 3+ events marked on top."""
    pts = data.get("bp_daily") or []
    base = data.get("baseline") or {}
    events = data.get("events") or []
    d = Drawing(width, height)
    left, right, top, bottom = 26, 34, 14, 16
    pw, ph = width - left - right, height - top - bottom

    vals = [v for p in pts for v in (p.get("systolic"), p.get("diastolic")) if v is not None]
    vals += [v for v in (base.get("systolic"), base.get("diastolic"), 140, 90) if v]
    if not pts or not [p for p in pts if p.get("systolic") is not None]:
        d.add(String(left, height / 2, "No blood pressure readings in this period.", fontName="Helvetica", fontSize=8, fillColor=MUTED))
        return d
    lo = int(min(vals) // 10 * 10 - 10)
    hi = int(-(-max(vals) // 10) * 10 + 10)
    n = len(pts)
    x = lambda i: left + (i / max(n - 1, 1)) * pw
    y = lambda v: bottom + (v - lo) / (hi - lo) * ph
    index = {p["date"]: i for i, p in enumerate(pts)}

    for v in range(lo, hi + 1, 20):
        d.add(Line(left, y(v), left + pw, y(v), strokeColor=RULE, strokeWidth=0.4))
        d.add(String(left - 4, y(v) - 2.5, str(v), fontName="Helvetica", fontSize=6.5, fillColor=MUTED, textAnchor="end"))

    # Reference line: the usual clinic threshold, so the GP can orient at a glance.
    d.add(Line(left, y(140), left + pw, y(140), strokeColor=MUTED, strokeWidth=0.5, strokeDashArray=[1, 2]))
    d.add(String(left + pw + 3, y(140) - 2.5, "140", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))

    for key in ("systolic", "diastolic"):
        b = base.get(key)
        if b:
            d.add(Line(left, y(b), left + pw, y(b), strokeColor=ACCENT, strokeWidth=0.8, strokeDashArray=[3, 2]))
    if base.get("systolic"):
        d.add(String(left + pw + 3, y(base["systolic"]) - 2.5, "usual", fontName="Helvetica", fontSize=6.5, fillColor=ACCENT))

    for key, width_ in (("systolic", 1.2), ("diastolic", 0.9)):
        run: list[float] = []
        for i, p in enumerate(pts):
            v = p.get(key)
            if v is None:
                if len(run) >= 4:
                    d.add(PolyLine(run, strokeColor=INK, strokeWidth=width_))
                run = []
                continue
            run += [x(i), y(v)]
            d.add(Circle(x(i), y(v), 1.2, fillColor=INK, strokeColor=None))
        if len(run) >= 4:
            d.add(PolyLine(run, strokeColor=INK, strokeWidth=width_))
    last = next((p for p in reversed(pts) if p.get("systolic") is not None), None)
    if last:
        i = index[last["date"]]
        d.add(String(x(i) + 3, y(last["systolic"]) + 2, "top", fontName="Helvetica", fontSize=6.5, fillColor=INK))
        d.add(String(x(i) + 3, y(last["diastolic"]) - 7, "bottom", fontName="Helvetica", fontSize=6.5, fillColor=INK))

    for e in events:
        i = index.get(e["date"])
        if i is None:
            continue
        _, c = RUNG.get(e["rung"], ("", WARN))
        d.add(Rect(x(i) - 1.2, bottom + ph + 3, 2.4, 6, fillColor=c, strokeColor=None))

    d.add(String(left, 3, _d(pts[0]["date"]), fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    d.add(String(left + pw, 3, _d(pts[-1]["date"]), fontName="Helvetica", fontSize=6.5, fillColor=MUTED, textAnchor="end"))
    return d


def _table(rows: list[list], widths: list[float]) -> Table:
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _story(data: dict) -> list:
    senior = data.get("senior") or {}
    period = data.get("period") or {}
    base = data.get("baseline") or {}
    adh = data.get("adherence") or {}
    events = data.get("events") or []
    words = data.get("in_their_words") or []
    aac = data.get("aac")
    note = data.get("note") or "Generated from the CareLoop decision log. Not connected to any clinic system."
    story: list = []

    story.append(Paragraph(f"GP brief: {_text(senior.get('name') or 'Unnamed')}", S_TITLE))
    sub = []
    if period.get("from") and period.get("to"):
        sub.append(f"{_dy(period['from'])} to {_dy(period['to'])}")
    if senior.get("conditions"):
        sub.append(", ".join(c.capitalize() for c in senior["conditions"]))
    appt = data.get("next_appointment")
    if appt:
        sub.append(f"Visit {_dy(appt['date'])}" + (f", {escape(appt['time'])}" if appt.get("time") else "")
                   + (f" at {_text(appt['place'])}" if appt.get("place") else ""))
    story.append(Paragraph(" · ".join(sub), S_SUB))
    story.append(Paragraph(escape(note), S_SMALL))
    story.append(Spacer(1, 5))

    # At a glance
    avg = _recent_avg(data.get("bp_daily") or [])
    glance = []
    if avg and base.get("systolic"):
        s, dia, k = avg
        diff = s - base["systolic"]
        glance.append(f"<b>Blood pressure, last 7 days:</b> average {s:.0f}/{dia:.0f} from {k} readings, against their own "
                      f"usual of {base['systolic']:.0f}/{base['diastolic']:.0f} ({'+' if diff >= 0 else ''}{diff:.0f} systolic).")
    elif avg:
        s, dia, k = avg
        glance.append(f"<b>Blood pressure, last 7 days:</b> average {s:.0f}/{dia:.0f} from {k} readings. No settled baseline yet.")
    else:
        glance.append("<b>Blood pressure:</b> no readings in the last 7 days.")
    if base.get("fallback"):
        glance.append("Baseline is a fallback value: too few readings to learn their own usual.")
    rep = adh.get("reported_days") or 0
    if rep:
        glance.append(f"<b>Medicines:</b> taken on {adh.get('taken_days', 0)} of {rep} days with a report; "
                      f"missed on {adh.get('missed_days', 0)}. Not reported on the other days.")
    else:
        glance.append("<b>Medicines:</b> no doses reported in this period.")
    for g in glance:
        story.append(Paragraph(g, S_BODY))
    meds = senior.get("medicines") or []
    if meds:
        story.append(Spacer(1, 2))
        med_line = "; ".join(f"{_text(m.get('name', '').capitalize())} {_text(m.get('dose_text', ''))}".strip()
                             + (f" (since {_dy(m['started'])})" if m.get("started") else "") for m in meds)
        story.append(Paragraph(f"<b>Taking:</b> {med_line}", S_BODY))
    story.append(Spacer(1, 6))

    # Chart
    story.append(Paragraph("Blood pressure, daily (mmHg)", S_H))
    story.append(_chart(data, BODY_W))
    caption = ("Dots are each day's reading, top line systolic and bottom diastolic. Dashed green: their own usual. "
               "Dotted: 140. Marks above the chart: events listed below (amber: noted or handed over; red: red flag).")
    first = next((p["date"] for p in data.get("bp_daily") or [] if p.get("systolic") is not None), None)
    if first and period.get("from") and first > period["from"]:
        caption += f" First reading on CareLoop: {_dy(first)}."
    gaps = sum(1 for p in data.get("bp_daily") or [] if p.get("systolic") is None and first and p["date"] > first)
    if gaps:
        caption += f" No reading on {gaps} day{'s' if gaps != 1 else ''} since then."
    story.append(Paragraph(caption, S_SMALL))
    story.append(Spacer(1, 6))

    # Events
    story.append(Paragraph("What CareLoop flagged", S_H))
    if events:
        shown = _pick(events, MAX_EVENTS, lambda e: e["rung"] == "R")
        rows = []
        for e in shown:
            label, c = RUNG.get(e["rung"], (f"Level {e['rung']}", INK))
            rows.append([
                Paragraph(_d(e["date"]), S_CELL),
                Paragraph(f'<font color="{c.hexval()}"><b>{label}</b></font>', S_CELL),
                Paragraph(_text(e.get("reason", "")), S_CELL),
                Paragraph(escape(e.get("decision_id", "")), S_CELL_MUTED),
            ])
        story.append(_table(rows, [16 * mm, 22 * mm, BODY_W - 16 * mm - 22 * mm - 34 * mm, 34 * mm]))
        if len(events) > len(shown):
            story.append(Paragraph(f"{len(events) - len(shown)} other events not shown (red flags always are); "
                                   "all are in the decision log.", S_SMALL))
    else:
        story.append(Paragraph("Nothing reached the level of a note in this period.", S_BODY))
    story.append(Spacer(1, 6))

    # In their own words
    story.append(Paragraph("In their own words", S_H))
    if words:
        shown = _pick(words, MAX_WORDS, lambda w: bool(DANGER & set(w.get("symptoms") or [])))
        rows = []
        for w in shown:
            sym = ", ".join(SYMPTOM.get(s, s.replace("_", " ")) for s in w.get("symptoms") or [])
            rows.append([
                Paragraph(_d(w["date"]), S_CELL),
                Paragraph(f"“{_text(w.get('said', ''))}”", S_CELL),
                Paragraph(escape(sym), S_CELL_MUTED),
            ])
        story.append(_table(rows, [16 * mm, BODY_W - 16 * mm - 40 * mm, 40 * mm]))
        if len(words) > len(shown):
            story.append(Paragraph(f"{len(words) - len(shown)} other reports not shown (danger symptoms always are).", S_SMALL))
    else:
        story.append(Paragraph("No symptoms reported in this period.", S_BODY))
    story.append(Spacer(1, 6))

    # Questions: the senior's own (from check-ins), then the family's (from the care notes)
    own = [q for w in words for q in (w.get("questions") or [])]
    family = data.get("family_questions") or []
    questions = own + family
    story.append(Paragraph("Questions for this visit", S_H))
    for q in own[:4]:
        story.append(Paragraph(f"• {_text(q)} <font color=\"#5f6660\">(asked by them)</font>", S_BODY))
    for q in family[: max(0, 6 - len(own[:4]))]:
        story.append(Paragraph(f"• {_text(q)} <font color=\"#5f6660\">(from family or centre)</font>", S_BODY))
    blank = max(0, 3 - len(questions))
    for _ in range(blank):
        story.append(_table([[""]], [BODY_W]))
        story.append(Spacer(1, 6))
    due = data.get("prevention_due") or []
    if due:
        story.append(Paragraph("<b>Vaccines and check-ups due or not recorded:</b> " + "; ".join(_text(d) for d in due[:6]) + ".", S_BODY))

    # AAC: the small bridge from primary care to the senior's centre
    if aac and aac.get("name"):
        story.append(Spacer(1, 4))
        going = aac.get("going") or []
        line = f"<b>Active Ageing Centre:</b> {_text(aac['name'])}."
        if going:
            line += " Going to: " + ", ".join(_text(g) for g in going) + "."
        story.append(Paragraph(line, S_BODY))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Each event above carries its decision log reference. Alert thresholds are placeholders until "
                           "a clinician signs them off. This brief does not diagnose or advise on medicines.", S_SMALL))
    return story


def gp_brief_pdf(data: dict) -> bytes:
    """The brief.json dict in, PDF bytes out. Always exactly one page."""
    buf = io.BytesIO()
    name = (data.get("senior") or {}).get("name") or "senior"
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
                            title=f"GP brief: {name}", author="CareLoop SG", subject="Generated from the CareLoop decision log")
    doc.build([KeepInFrame(BODY_W, H - 2 * MARGIN, _story(data), mode="shrink")])
    return buf.getvalue()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -m backend.reports.gp_brief brief.json out.pdf")
    with open(sys.argv[1], encoding="utf-8") as f:
        pdf = gp_brief_pdf(json.load(f))
    with open(sys.argv[2], "wb") as f:
        f.write(pdf)
    print(f"wrote {sys.argv[2]} ({len(pdf):,} bytes)")
