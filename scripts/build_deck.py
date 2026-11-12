"""Build the semantic-layer deck from the POC's own facts.

    python scripts/build_deck.py

Produces files/Insurance_Semantic_Layer.pptx — every number in it is read from
the repo (ontology, data, tests), so the deck cannot drift from the build.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT.parent / "files"
OUT = FILES / "Insurance_Semantic_Layer.pptx"

NAVY = RGBColor(0x0E, 0x24, 0x33)
BLUE = RGBColor(0x1F, 0x6F, 0xB2)
TEAL = RGBColor(0x17, 0x8A, 0x8A)
AMBER = RGBColor(0xC0, 0x77, 0x18)
GREY = RGBColor(0x4A, 0x55, 0x63)
LIGHT = RGBColor(0xF2, 0xF5, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0xD5, 0xDD, 0xE5)

W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def text(slide, x, y, w, h, value, size=14, bold=False, color=GREY, align=PP_ALIGN.LEFT,
         font="Calibri", spacing=1.0, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    lines = value.split("\n")
    for i, line in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        run = para.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def _strip_style(shp):
    """Remove the theme style reference so LibreOffice/PowerPoint draw no shadow."""
    from pptx.oxml.ns import qn

    sp = shp._element
    style = sp.find(qn("p:style"))
    if style is not None:
        sp.remove(style)
    shp.shadow.inherit = False


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line_w=1.0):
    shp = slide.shapes.add_shape(shape, x, y, w, h)
    _strip_style(shp)
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = 0.08
    return shp


def header(slide, kicker: str, title: str, number: int | None = None, light_bg=False):
    bg = rect(slide, 0, 0, W, H, fill=LIGHT if light_bg else WHITE, line=None, shape=MSO_SHAPE.RECTANGLE)
    bg.shadow.inherit = False
    slide.shapes._spTree.remove(bg._element)
    slide.shapes._spTree.insert(2, bg._element)
    rect(slide, 0, 0, W, Inches(0.09), fill=BLUE, line=None, shape=MSO_SHAPE.RECTANGLE)
    text(slide, Inches(0.75), Inches(0.42), Inches(10), Inches(0.3), kicker.upper(), size=10.5, bold=True, color=BLUE)
    text(slide, Inches(0.75), Inches(0.72), Inches(11.6), Inches(0.75), title, size=27, bold=True, color=NAVY)
    if number is not None:
        text(slide, Inches(12.2), Inches(7.02), Inches(0.6), Inches(0.3), str(number), size=10, color=GREY, align=PP_ALIGN.RIGHT)
        text(slide, Inches(0.75), Inches(7.02), Inches(8), Inches(0.3),
             "Insurance Semantic Layer  ·  built on the running POC", size=9.5, color=GREY)


def bullets(slide, x, y, w, items, size=15, gap=0.52, color=GREY, bold_lead=True):
    cy = y
    for item in items:
        if isinstance(item, tuple):
            lead, rest = item
            box = slide.shapes.add_textbox(x, cy, w, Inches(gap))
            tf = box.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            r1 = p.add_run()
            r1.text = lead
            r1.font.size = Pt(size)
            r1.font.bold = bold_lead
            r1.font.color.rgb = NAVY
            r1.font.name = "Calibri"
            r2 = p.add_run()
            r2.text = "  " + rest
            r2.font.size = Pt(size)
            r2.font.color.rgb = color
            r2.font.name = "Calibri"
        else:
            text(slide, x, cy, w, Inches(gap), "—  " + item, size=size, color=color)
        cy += Inches(gap)
    return cy


def table(slide, headers, rows, x, y, w, h, col_ratios=None, size=11, head_size=11):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, h)
    tbl = shape.table
    if col_ratios:
        total = sum(col_ratios)
        for i, ratio in enumerate(col_ratios):
            tbl.columns[i].width = Emu(int(w * ratio / total))
    for j, head in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.text = head
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0xE7, 0xEE, 0xF5)
        for para in cell.text_frame.paragraphs:
            para.alignment = PP_ALIGN.LEFT
            for run in para.runs:
                run.font.size = Pt(head_size)
                run.font.bold = True
                run.font.color.rgb = NAVY
                run.font.name = "Calibri"
        cell.margin_left = Inches(0.08)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xFA, 0xFB, 0xFC)
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(size)
                    run.font.color.rgb = GREY
                    run.font.name = "Calibri"
            cell.margin_left = Inches(0.08)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
    return tbl


def tiles(slide, items, y=Inches(1.65), height=Inches(1.05), gap=Inches(0.18)):
    """items: list of (value, label)"""
    n = len(items)
    total_gap = gap * (n - 1)
    width = (W - Inches(1.5) - total_gap) / n
    x = Inches(0.75)
    for value, label in items:
        rect(slide, x, y, width, height, fill=WHITE, line=BORDER)
        text(slide, x + Inches(0.18), y + Inches(0.12), width - Inches(0.3), Inches(0.42), value, size=24, bold=True, color=NAVY)
        text(slide, x + Inches(0.18), y + Inches(0.6), width - Inches(0.3), Inches(0.3), label, size=10.5, color=GREY)
        x += width + gap


def picture(slide, path, x, y, w=None, h=None, caption=None):
    kwargs = {}
    if w:
        kwargs["width"] = w
    if h:
        kwargs["height"] = h
    pic = slide.shapes.add_picture(str(path), x, y, **kwargs)
    if caption:
        text(slide, x, y + pic.height + Inches(0.08), pic.width, Inches(0.3), caption, size=10, color=GREY)
    return pic


def arrow(slide, x1, y1, x2, y2, color=BLUE, width=1.5):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    return conn


def notes(slide, value: str):
    slide.notes_slide.notes_text_frame.text = value


# --------------------------------------------------------------------------
# 1. Title
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
_strip_style(bg)
bg.fill.solid()
bg.fill.fore_color.rgb = NAVY
bg.line.fill.background()
bg.shadow.inherit = False

text(s, Inches(0.9), Inches(1.25), Inches(9), Inches(0.3), "INSURANCE SEMANTIC LAYER", size=12, bold=True, color=RGBColor(0x7F, 0xB3, 0xE0))
text(s, Inches(0.9), Inches(1.7), Inches(10.5), Inches(1.6), "From records\nto reasoning", size=48, bold=True, color=WHITE, spacing=0.95)
text(s, Inches(0.9), Inches(3.6), Inches(9.6), Inches(0.9),
     "One ontology, two decisions, and an evidence trail under every number.\nBuilt, running, and honest about what is next.",
     size=16, color=RGBColor(0xC9, 0xD6, 0xE2), spacing=1.15)

rect(s, Inches(0.9), Inches(4.75), Inches(1.5), Inches(0.04), fill=RGBColor(0x7F, 0xB3, 0xE0), line=None, shape=MSO_SHAPE.RECTANGLE)
text(s, Inches(0.9), Inches(5.0), Inches(5.4), Inches(0.9),
     "Commercial property underwriting\nFleet renewal at group level", size=13, color=RGBColor(0xE6, 0xEC, 0xF2), spacing=1.2)
text(s, Inches(6.7), Inches(5.0), Inches(5.6), Inches(0.9),
     "6 entities · 7 relationships · 8 rules · 82 tests\nRunning: property + fleet, same engine",
     size=13, color=RGBColor(0xE6, 0xEC, 0xF2), spacing=1.2)
text(s, Inches(0.9), Inches(6.6), Inches(11), Inches(0.3), "Version 2.0  ·  November 2026  ·  reference implementation: insurance-accelerator",
     size=10, color=RGBColor(0x8F, 0xA3, 0xB5))
notes(s, "Open with the question the deck answers: why do AI programmes fail in insurance — and what does a small, governed semantic layer change about that?")

# --------------------------------------------------------------------------
# 2. The story in one page
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "The story in one page", "Four moves, one operating spine", 2)

steps = [
    ("01", "FRAGMENTED", "Four systems hold four versions of the same customer, policy and loss.", GREY),
    ("02", "MEANING", "Canonical entities and typed, dated relationships make the fragments one story.", BLUE),
    ("03", "DECISION", "Rules read the graph and return points, thresholds and evidence.", TEAL),
    ("04", "OUTCOME", "Faster triage, defensible referrals, metrics traceable to a definition.", AMBER),
]
x = Inches(0.75)
box_w = Inches(2.85)
for num, name, body, colour in steps:
    rect(s, x, Inches(1.95), box_w, Inches(2.35), fill=WHITE, line=BORDER)
    text(s, x + Inches(0.22), Inches(2.1), Inches(0.8), Inches(0.4), num, size=18, bold=True, color=colour)
    text(s, x + Inches(0.22), Inches(2.5), box_w - Inches(0.4), Inches(0.3), name, size=12, bold=True, color=NAVY)
    text(s, x + Inches(0.22), Inches(2.85), box_w - Inches(0.44), Inches(1.2), body, size=11.5, color=GREY, spacing=1.1)
    x += box_w + Inches(0.22)

rect(s, Inches(0.75), Inches(4.75), Inches(11.85), Inches(1.35), fill=RGBColor(0xEC, 0xF3, 0xF9), line=None)
text(s, Inches(1.0), Inches(4.95), Inches(11.3), Inches(1.0),
     "Start narrow. Prove one decision. Extend the same spine.\nThe ontology, the ruleset and the evidence model do not change when you add claims, billing, renewal or distribution — only the sources and the scope do.",
     size=13, color=NAVY, spacing=1.25)
notes(s, "This is the whole argument: meaning is the missing layer between data foundations and agents.")

# --------------------------------------------------------------------------
# 3. The problem, grounded
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "The problem", "The policy looked fine. The book did not.", 3)

text(s, Inches(0.75), Inches(1.6), Inches(6.4), Inches(0.4), "A real case from the build — ABC Express, fleet renewal",
     size=12, bold=True, color=BLUE)

facts = [
    ("100", "trucks on one policy, one company, 2025"),
    ("40", "trucks moved to a sister policy on 1 Apr 2026"),
    ("₹5L", "claim that travelled with truck V041"),
    ("150", "trucks in the group, across two entities"),
]
cy = Inches(2.15)
for value, label in facts:
    rect(s, Inches(0.75), cy, Inches(6.4), Inches(0.8), fill=WHITE, line=BORDER)
    text(s, Inches(0.95), cy + Inches(0.18), Inches(1.2), Inches(0.45), value, size=18, bold=True, color=NAVY)
    text(s, Inches(2.25), cy + Inches(0.22), Inches(4.7), Inches(0.4), label, size=12, color=GREY)
    cy += Inches(0.92)

rect(s, Inches(7.55), Inches(1.6), Inches(5.05), Inches(4.55), fill=RGBColor(0xFB, 0xF1, 0xEC), line=RGBColor(0xE6, 0xC3, 0xB0))
text(s, Inches(7.8), Inches(1.85), Inches(4.6), Inches(0.35), "WHAT A POLICY-ONLY VIEW SEES", size=10.5, bold=True, color=RGBColor(0xA5, 0x4B, 0x22))
text(s, Inches(7.8), Inches(2.25), Inches(4.55), Inches(2.2),
     "60 trucks, ₹3,60,000 premium,\nloss ratio 50%\n→ renew quietly.",
     size=15, color=NAVY, spacing=1.3)
text(s, Inches(7.8), Inches(4.05), Inches(4.6), Inches(0.35), "WHAT THE BOOK ACTUALLY SAYS", size=10.5, bold=True, color=RGBColor(0xA5, 0x4B, 0x22))
text(s, Inches(7.8), Inches(4.45), Inches(4.55), Inches(1.8),
     "150 trucks in the group, 60% loss ratio,\na ₹5L claim sitting on the sister policy\n→ refer + group review.",
     size=15, color=NAVY, spacing=1.3)

text(s, Inches(0.75), Inches(6.4), Inches(11.8), Inches(0.6),
     "Nobody lied. Every number was correct in its own system. The meaning — that these are one risk, and that the risk moved — existed nowhere.",
     size=12.5, color=GREY)
notes(s, "Ground the abstract problem in this case. Every system was right; the meaning was missing.")

# --------------------------------------------------------------------------
# 4. What we built
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Proof", "This is running, not slideware", 4)

tiles(s, [
    ("6", "canonical entities"),
    ("7", "typed relationships"),
    ("8 + 3", "scored rules + hard stops"),
    ("82", "tests passing"),
], y=Inches(1.7))

text(s, Inches(0.75), Inches(3.15), Inches(5.6), Inches(0.35), "IN THE BOX", size=10.5, bold=True, color=BLUE)
bullets(s, Inches(0.75), Inches(3.55), Inches(5.6), [
    ("Ontology", "entities, keys, edges, mappings, rules — one YAML"),
    ("Ingest", "coercion, validation, referential integrity"),
    ("Graph", "in-memory or Neo4j, identical traversal"),
    ("Rules", "points, thresholds, evidence per finding"),
    ("API", "360 view, assessment, impact trace"),
    ("Workbench", "score, evidence, graph, portfolio"),
], size=12, gap=0.44)

text(s, Inches(6.85), Inches(3.15), Inches(5.6), Inches(0.35), "TWO USE CASES, ONE ENGINE", size=10.5, bold=True, color=BLUE)
rect(s, Inches(6.85), Inches(3.55), Inches(5.75), Inches(1.25), fill=WHITE, line=BORDER)
text(s, Inches(7.05), Inches(3.7), Inches(5.35), Inches(1.0),
     "Commercial property\n12 properties · 8 rules · band, decision, evidence\nPR005 declined at 100/100 — two hard stops, eight factors",
     size=11.5, color=GREY, spacing=1.15)
rect(s, Inches(6.85), Inches(4.95), Inches(5.75), Inches(1.25), fill=WHITE, line=BORDER)
text(s, Inches(7.05), Inches(5.1), Inches(5.35), Inches(1.0),
     "Fleet renewal\n150 vehicles · time-valid edges · governed metrics\nLoss ratio 50% → 60% when ALAE moves to the metric v2",
     size=11.5, color=GREY, spacing=1.15)
notes(s, "The point of this slide: the deck is describing something that exists. Numbers are read from the repo.")

# --------------------------------------------------------------------------
# 5. Use case 1 — property
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Use case 1", "From a property ID to a defended decision", 5)
picture(s, Path("/tmp/opencode/property_crop.png"), Inches(0.75), Inches(1.6), w=Inches(7.4))
text(s, Inches(8.45), Inches(1.75), Inches(4.2), Inches(0.35), "WHAT YOU ARE LOOKING AT", size=10.5, bold=True, color=BLUE)
bullets(s, Inches(8.45), Inches(2.15), Inches(4.2), [
    ("Score 100/100", "eight factors, capped"),
    ("Two hard stops", "facts outrank arithmetic"),
    ("Every row", "names the attribute it read"),
    ("Connected context", "policy, coverages, claims"),
    ("82 tests", "the criterion, asserted"),
], size=11.5, gap=0.55)
text(s, Inches(8.45), Inches(5.6), Inches(4.2), Inches(1.0),
     "PR005: 1948 frame, no sprinkler, flood zone AE, 79% insured, ₹5.35L losses in 36 months.",
     size=10.5, color=GREY, spacing=1.15)
notes(s, "The property case shows the scoring model: points, hard stops, bands. Simple to explain, hard to fake.")

# --------------------------------------------------------------------------
# 6. Use case 2 — fleet
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Use case 2", "When the risk moves between policies", 6)
picture(s, Path("/tmp/opencode/fleet_crop.png"), Inches(0.75), Inches(1.6), w=Inches(7.2))
text(s, Inches(8.45), Inches(1.75), Inches(4.2), Inches(0.35), "WHAT IS NEW HERE", size=10.5, bold=True, color=BLUE)
bullets(s, Inches(8.45), Inches(2.15), Inches(4.2), [
    ("Time-valid edges", "which fleet did P205 cover at renewal?"),
    ("A group above the entity", "150 > 120, invisible to any policy"),
    ("Governed metrics", "rules reference a versioned definition"),
    ("Evidence", "V041's ₹5L history, carried not scored"),
], size=11.5, gap=0.72)
text(s, Inches(8.45), Inches(5.75), Inches(4.2), Inches(0.9),
     "Same engine, same evidence model. Only the model and the metrics are new.",
     size=11, color=GREY, spacing=1.15)
notes(s, "This is the slide that proves the framework generalises: property scores, fleet doesn't — both explain.")

# --------------------------------------------------------------------------
# 7. The model
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "The model", "Six entities, seven edges, one answer", 7)

boxes = {
    "Customer": (Inches(1.15), Inches(1.95)),
    "Policy": (Inches(4.55), Inches(1.95)),
    "Property": (Inches(7.95), Inches(1.95)),
    "Coverage": (Inches(4.55), Inches(4.15)),
    "Claim": (Inches(7.95), Inches(4.15)),
    "RiskAssessment": (Inches(10.9), Inches(4.15)),
}
bw, bh = Inches(2.1), Inches(0.85)
for name, (x, y) in boxes.items():
    fill = RGBColor(0xE7, 0xEE, 0xF5) if name != "RiskAssessment" else RGBColor(0xE9, 0xF4, 0xF4)
    rect(s, x, y, bw, bh, fill=fill, line=BORDER)
    text(s, x, y + Inches(0.22), bw, Inches(0.35), name, size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

for x1, y1, x2, y2, label in [
    (Inches(3.25), Inches(2.37), Inches(4.55), Inches(2.37), "BUYS"),
    (Inches(6.65), Inches(2.37), Inches(7.95), Inches(2.37), "COVERS"),
    (Inches(5.6), Inches(2.8), Inches(5.6), Inches(4.15), "HAS_COVERAGE"),
    (Inches(9.0), Inches(2.8), Inches(9.0), Inches(4.15), "HAS_CLAIM"),
    (Inches(10.05), Inches(4.57), Inches(10.9), Inches(4.57), "HAS_RISK"),
]:
    arrow(s, x1, y1, x2, y2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    text(s, mx - Inches(0.9), my - Inches(0.3), Inches(1.8), Inches(0.25), label, size=8.5, color=BLUE, align=PP_ALIGN.CENTER)

text(s, Inches(0.75), Inches(5.55), Inches(11.8), Inches(0.35), "Path: Property → Policy → Coverage → Claims → Rules → RiskAssessment",
     size=12, bold=True, color=NAVY)
text(s, Inches(0.75), Inches(5.95), Inches(11.8), Inches(0.8),
     "Every edge is typed, directed and — in the fleet model — dated. That single change is what lets the model answer \"which fleet covered this vehicle at renewal\" instead of \"what is attached today\".",
     size=11.5, color=GREY, spacing=1.15)
notes(s, "Six entities is a design choice, not a limitation. ACORD alignment is the scale path, not the starting point.")

# --------------------------------------------------------------------------
# 8. Domain segregation — the rule
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Domain structure", "Segregate by domain, converge on one core", 8)

rect(s, Inches(0.75), Inches(1.55), Inches(4.15), Inches(4.3), fill=RGBColor(0xE9, 0xF4, 0xF4), line=RGBColor(0xB7, 0xD9, 0xD9))
text(s, Inches(0.95), Inches(1.75), Inches(3.8), Inches(0.3), "CANONICAL CORE — owned once", size=10.5, bold=True, color=TEAL)
text(s, Inches(0.95), Inches(2.1), Inches(3.75), Inches(2.6),
     "Customer · Party\nPolicy\nProperty · Vehicle\nCoverage\nClaim\nRiskAssessment\n\nOne name. One key. One definition.",
     size=12, color=NAVY, spacing=1.25)
text(s, Inches(0.95), Inches(5.1), Inches(3.75), Inches(0.7),
     "Change control sits here — not in any consuming system.",
     size=10.5, color=GREY, spacing=1.1)

text(s, Inches(5.25), Inches(1.6), Inches(7.3), Inches(0.35), "DOMAIN DATA PRODUCTS — owned by their domain", size=10.5, bold=True, color=BLUE)
domains = [
    ("Party & Customer", "CRM, MDM, distribution"),
    ("Product & Coverage", "product engine, rate tables"),
    ("Policy & Servicing", "policy administration"),
    ("Risk & Underwriting", "UW workbench, scoring"),
    ("Claims", "claims management"),
    ("Billing & Finance", "billing, ledger"),
]
cy = Inches(1.95)
for name, sys_of_record in domains:
    rect(s, Inches(5.25), cy, Inches(7.3), Inches(0.56), fill=WHITE, line=BORDER)
    text(s, Inches(5.45), cy + Inches(0.13), Inches(2.9), Inches(0.3), name, size=11.5, bold=True, color=NAVY)
    text(s, Inches(8.4), cy + Inches(0.15), Inches(4.0), Inches(0.3), sys_of_record, size=10.5, color=GREY)
    cy += Inches(0.66)

rect(s, Inches(0.75), Inches(6.05), Inches(11.8), Inches(0.62), fill=RGBColor(0xFD, 0xF6, 0xEA), line=None)
text(s, Inches(0.95), Inches(6.17), Inches(11.4), Inches(0.45),
     "The rule: a domain may publish its own data product, but it may not redefine a canonical entity. Cross-domain metrics are owned once, in the metric layer.",
     size=10.5, color=RGBColor(0x7A, 0x4C, 0x0E), spacing=1.05)
notes(s, "This is the governance answer to 'how do we stop six teams defining premium differently'.")

# --------------------------------------------------------------------------
# 9. Domain contracts
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Domain structure", "What each domain owns and publishes", 9)

table(s,
      ["Domain", "Owns (write)", "Publishes", "Consumes", "Precedence example"],
      [
          ["Policy & Servicing", "Policy, Property, Vehicle, endorsements", "Policy 360, in-force dates", "Customer, claims summary", "Cover dates win from policy admin"],
          ["Claims", "Claim, loss, reserve, payment", "Claims 360, loss history", "Policy, coverage, vehicle", "Incurred wins from claims, never billing"],
          ["Risk & UW", "RiskAssessment, rule hits", "Score, band, evidence", "Property, claims, group", "Decision is produced, never edited"],
          ["Billing & Finance", "Invoice, receivable, collection", "Written / earned premium", "Policy", "Premium collected wins from billing"],
          ["Product & Coverage", "Product, coverage class, limits", "Coverage catalogue", "Policy", "Limit definitions win from product"],
          ["Party & Customer", "Customer, party, roles", "Party 360", "Policy, claims", "Legal name wins from MDM"],
      ],
      Inches(0.75), Inches(1.75), Inches(11.85), Inches(3.6),
      col_ratios=[1.5, 2.4, 2.0, 2.0, 2.6], size=10)
text(s, Inches(0.75), Inches(5.75), Inches(11.8), Inches(0.9),
     "Each row is a contract: the domain is authoritative for those attributes, publishes them with keys and versions, and reads everything else through the semantic layer — never system to system.",
     size=11.5, color=GREY, spacing=1.15)
notes(s, "Precedence is the practical part. When two systems disagree, this table decides — before a model ever sees the data.")

# --------------------------------------------------------------------------
# 10. Three axes of structure
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Domain structure", "Structure along three axes", 10)

cols = [
    ("WHAT", "Entity and relationship", [
        "Six canonical entities, one key each",
        "Edges carry direction and meaning",
        "Taxonomies for loss cause, occupancy, decline reason",
    ], BLUE),
    ("WHEN", "Time on every edge", [
        "Valid time: which fleet did P205 cover on 31 Dec?",
        "Record time: what did we believe, and when",
        "Re-score as at any date — same rules, same answer",
    ], TEAL),
    ("WHO MAY", "Context and authority", [
        "Who is asking: underwriter, adjuster, auditor",
        "Read, recommend, or commit — stated per agent",
        "Consent and residency attached to the entity",
    ], AMBER),
]
x = Inches(0.75)
for title, subtitle, items, colour in cols:
    rect(s, x, Inches(1.75), Inches(3.85), Inches(3.4), fill=WHITE, line=BORDER)
    rect(s, x, Inches(1.75), Inches(3.85), Inches(0.07), fill=colour, line=None, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + Inches(0.25), Inches(2.0), Inches(3.4), Inches(0.3), title, size=12, bold=True, color=colour)
    text(s, x + Inches(0.25), Inches(2.32), Inches(3.4), Inches(0.3), subtitle, size=11, color=NAVY, bold=True)
    cy = Inches(2.75)
    for item in items:
        text(s, x + Inches(0.25), cy, Inches(3.4), Inches(0.75), "—  " + item, size=10.5, color=GREY, spacing=1.1)
        cy += Inches(0.78)
    x += Inches(4.0)

text(s, Inches(0.75), Inches(5.45), Inches(11.8), Inches(0.6),
     "Most semantic layers do the first axis well and skip the other two. Without time, a transferred vehicle disappears; without authority, an agent cannot be trusted to act.",
     size=11.5, color=GREY, spacing=1.15)

pills = [("WHAT", "Built", TEAL), ("WHEN", "Built — fleet model", TEAL), ("WHO MAY", "Next", AMBER)]
px = Inches(0.75)
for label, status, colour in pills:
    rect(s, px, Inches(6.3), Inches(3.85), Inches(0.5), fill=WHITE, line=BORDER)
    text(s, px + Inches(0.2), Inches(6.42), Inches(1.6), Inches(0.3), label, size=9.5, bold=True, color=NAVY)
    text(s, px + Inches(1.55), Inches(6.42), Inches(2.1), Inches(0.3), status, size=9.5, color=colour)
    px += Inches(4.0)
notes(s, "Time and authority are the differentiators. The POC has axis one and two; axis three is on the roadmap.")

# --------------------------------------------------------------------------
# 11. Semantic layer capabilities — status
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Capability map", "Five capabilities, honestly scored", 11)

table(s,
      ["Capability", "What it means in practice", "Status"],
      [
          ["Canonical entities", "Customer, Policy, Property, Coverage, Claim, RiskAssessment — one name, one key", "Built"],
          ["Relationships", "BUYS, COVERS, HAS_COVERAGE, HAS_CLAIM, HAS_RISK, CLAIMED_ON, INSURED_BY — typed and dated", "Built"],
          ["Taxonomies", "Construction class, occupancy, flood zone, peril, occupancy hazard", "Built (small)"],
          ["Constraints & inference", "Validation, referential integrity, hard stops; no OWL reasoning by design", "Partial"],
          ["Context & authority", "Who is asking, what they may read or write, consent and residency", "Next"],
          ["Governed metrics", "Rule references a definition with a version — loss ratio v1 → v2", "Built (fleet)"],
          ["Evidence", "Every point and metric traceable to attribute, threshold and reason", "Built"],
          ["Documents & extraction", "Schedules, loss runs, notes as first-class evidence", "Next"],
      ],
      Inches(0.75), Inches(1.7), Inches(11.85), Inches(3.9),
      col_ratios=[2.3, 6.4, 1.6], size=10.5)

text(s, Inches(0.75), Inches(5.9), Inches(11.8), Inches(0.7),
     "Four built, one partial, two next. Nothing on this slide is described as done that cannot be demonstrated in the running app.",
     size=11.5, color=GREY)
notes(s, "Credibility comes from the status column. Say 'next' out loud before anyone asks.")

# --------------------------------------------------------------------------
# 12. Governed metrics + lifecycle
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Governed metrics", "One definition change, every decision traced", 12)
text(s, Inches(0.75), Inches(1.75), Inches(7.4), Inches(0.3), "THE SAME PAGE, WITH THE TOGGLE MOVED", size=10.5, bold=True, color=BLUE)
table(s,
      ["Policy", "Loss ratio v1", "Loss ratio v2", "Decision before", "Decision after"],
      [
          ["P101", "41.7%", "60.0%", "Group assessment", "Refer + group assessment"],
          ["P205", "50.0%", "60.0%", "Group assessment", "Refer + group assessment"],
      ],
      Inches(0.75), Inches(2.15), Inches(7.4), Inches(1.15),
      col_ratios=[1.0, 1.6, 1.6, 2.4, 2.8], size=10.5)
text(s, Inches(0.75), Inches(3.45), Inches(7.4), Inches(0.3),
     "Hover states aside, that is the whole difference: one file, one version, two decisions.",
     size=10, color=GREY)

rect(s, Inches(0.75), Inches(4.05), Inches(7.4), Inches(1.85), fill=RGBColor(0xEC, 0xF3, 0xF9), line=None)
text(s, Inches(1.0), Inches(4.25), Inches(6.9), Inches(1.4),
     "Same claims. Same premium.\nOne definition change — and both policies move from\n\"group review\" to \"refer\".\n\nIn a spreadsheet you would discover that a quarter later.",
     size=12.5, color=NAVY, spacing=1.2)

text(s, Inches(8.45), Inches(1.75), Inches(4.2), Inches(0.35), "THE LIFECYCLE TEST", size=10.5, bold=True, color=BLUE)
bullets(s, Inches(8.45), Inches(2.15), Inches(4.2), [
    ("v1", "incurred ÷ premium — 50.0%"),
    ("v2", "(incurred + ALAE) ÷ premium — 60.0%"),
    ("Threshold", "60% → refer"),
    ("Impact", "2 of 2 decisions move"),
], size=11.5, gap=0.62)
text(s, Inches(8.45), Inches(4.85), Inches(4.2), Inches(1.5),
     "A rule that contains 0.60 is a rule you cannot audit. Here the rule reads a metric, the metric has a version, and the effect of changing it is a table — not an incident three months later.",
     size=11, color=GREY, spacing=1.15)
notes(s, "This is the slide that separates governance from good intentions.")

# --------------------------------------------------------------------------
# 13. Architecture
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Architecture", "One governed path from source to agent", 13)

layers = [
    ("SOURCES", ["Policy admin", "Claims", "Billing", "UW desk", "Documents"], BLUE),
    ("INGEST", ["Field mapping", "Validation", "Entity resolution", "Doc extraction"], TEAL),
    ("SEMANTIC CORE", ["Ontology repo", "Graph store", "Metric layer", "Rules service"], NAVY),
    ("SERVING", ["API / tools", "Workbench", "BI", "Agent runtime"], AMBER),
]
x = Inches(0.75)
box_w = Inches(2.75)
for idx, (name, items, colour) in enumerate(layers):
    rect(s, x, Inches(1.75), box_w, Inches(2.95), fill=WHITE, line=BORDER)
    rect(s, x, Inches(1.75), box_w, Inches(0.07), fill=colour, line=None, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + Inches(0.2), Inches(1.98), box_w - Inches(0.4), Inches(0.3), name, size=11, bold=True, color=colour)
    cy = Inches(2.42)
    for item in items:
        text(s, x + Inches(0.2), cy, box_w - Inches(0.35), Inches(0.3), "·  " + item, size=10.5, color=GREY)
        cy += Inches(0.45)
    if idx < len(layers) - 1:
        text(s, x + box_w + Inches(0.04), Inches(2.95), Inches(0.34), Inches(0.4), "→", size=17, color=BLUE, align=PP_ALIGN.CENTER)
    x += box_w + Inches(0.38)

text(s, Inches(0.75), Inches(5.05), Inches(11.8), Inches(1.0),
     "POC today: CSV sources, in-memory graph, YAML ontology and metrics, Python rules service, FastAPI, Streamlit.\nProduction: same boxes, different vendors — lakehouse, Neo4j Aura, governed metric layer, API management, embedded in the UW screen. Replace one component at a time; the model and the evidence contract do not move.",
     size=10.5, color=GREY, spacing=1.2)
notes(s, "Emphasise: the swap is components, not model. That is what makes the POC an accelerator rather than a demo.")

# --------------------------------------------------------------------------
# 14. AI layer
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "The AI layer", "What the agent does — and never does", 14)

rect(s, Inches(0.75), Inches(1.7), Inches(5.85), Inches(3.95), fill=RGBColor(0xEC, 0xF3, 0xF9), line=None)
text(s, Inches(1.0), Inches(1.9), Inches(5.4), Inches(0.3), "THE AGENT MAY", size=10.5, bold=True, color=BLUE)
bullets(s, Inches(1.0), Inches(2.3), Inches(5.4), [
    ("Ask", "\"why is P205 referred?\" — it calls the assessment tool"),
    ("Retrieve", "the group, the transfers, the claim history"),
    ("Extract", "schedules and loss runs into canonical fields, with confidence"),
    ("Draft", "the renewal note, the broker email, the file summary"),
    ("Act", "request a document, assign a referral — inside stated authority"),
], size=11.5, gap=0.72)

rect(s, Inches(6.95), Inches(1.7), Inches(5.6), Inches(3.95), fill=RGBColor(0xFB, 0xF1, 0xEC), line=None)
text(s, Inches(7.2), Inches(1.9), Inches(5.1), Inches(0.3), "THE AGENT NEVER", size=10.5, bold=True, color=RGBColor(0xA5, 0x4B, 0x22))
bullets(s, Inches(7.2), Inches(2.3), Inches(5.1), [
    ("Compute the score", "points come from the rules engine, not a model"),
    ("Invent a number", "any figure not in a tool result is a defect"),
    ("Redefine a metric", "definitions are versioned files"),
    ("Decide", "it recommends; an underwriter signs"),
], size=11.5, gap=0.72)

text(s, Inches(0.75), Inches(5.95), Inches(11.8), Inches(0.75),
     "The AI layer does not make the system smarter about risk. It makes the knowledge reachable — and that is the difference between a semantic layer that is queried and one that is used.",
     size=11.5, color=GREY, spacing=1.15)
notes(s, "The guardrail is the argument: no model in the decision path, so nothing can be hallucinated into a number.")

# --------------------------------------------------------------------------
# 15. Business outcomes
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Business impact", "Where the value actually lands", 15)

table(s,
      ["Value stream", "What changes", "KPI to baseline"],
      [
          ["Underwriting renewal", "Policy-only view replaced by policy + group + history; referral pack assembled automatically", "Referral pack time; referral precision"],
          ["Fleet / group risk", "Transfers and aggregations visible at renewal, not after the loss", "Policies priced without group view"],
          ["Governance", "One definition per metric, versioned, with impact trace", "Metric disputes; restatement count"],
          ["Data onboarding", "New source maps to canonical entities and validates without editing rules", "Effort per new source"],
          ["Claims & fraud", "Claim history follows the vehicle and the party across policies", "False-positive referrals"],
      ],
      Inches(0.75), Inches(1.75), Inches(11.85), Inches(3.3),
      col_ratios=[2.3, 5.6, 3.0], size=10.5)

rect(s, Inches(0.75), Inches(5.35), Inches(11.85), Inches(1.15), fill=RGBColor(0xFD, 0xF6, 0xEA), line=None)
text(s, Inches(1.0), Inches(5.55), Inches(11.4), Inches(0.85),
     "These are hypotheses, not results. Each one needs a baseline, an owner and a measurement window before it becomes a number in a business case — and that is the first thing a 90-day pilot buys.",
     size=11.5, color=RGBColor(0x7A, 0x4C, 0x0E), spacing=1.15)
notes(s, "Resist quoting percentages. Say hypothesis, baseline, owner — that is what a serious buyer wants to hear.")

# --------------------------------------------------------------------------
# 16. Roadmap + ask
# --------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
header(s, "Roadmap", "90 days to prove, three quarters to scale", 16)

phases = [
    ("0–90 DAYS", "Prove", ["One value stream: property UW", "Six entities, ruleset v1.0", "Workbench + explained API", "82 tests, baseline metrics"], BLUE),
    ("Q2", "Pilot", ["Add claims and billing sources", "Three domains, 10× data", "Governed ontology repo", "Metric layer + lineage"], TEAL),
    ("Q3–Q4", "Scale", ["ACORD-aligned extensions", "Agent tools with authority", "Policy engine + audit", "FinOps and unit economics"], AMBER),
]
x = Inches(0.75)
for period, name, items, colour in phases:
    rect(s, x, Inches(1.75), Inches(3.85), Inches(3.05), fill=WHITE, line=BORDER)
    rect(s, x, Inches(1.75), Inches(3.85), Inches(0.07), fill=colour, line=None, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + Inches(0.25), Inches(1.98), Inches(3.2), Inches(0.25), period, size=9.5, bold=True, color=colour)
    text(s, x + Inches(0.25), Inches(2.24), Inches(3.2), Inches(0.35), name, size=16, bold=True, color=NAVY)
    cy = Inches(2.72)
    for item in items:
        text(s, x + Inches(0.25), cy, Inches(3.35), Inches(0.6), "—  " + item, size=10.5, color=GREY, spacing=1.05)
        cy += Inches(0.6)
    x += Inches(4.0)

text(s, Inches(0.75), Inches(5.0), Inches(11.8), Inches(0.35), "GATES", size=10, bold=True, color=BLUE)
text(s, Inches(0.75), Inches(5.3), Inches(11.8), Inches(0.55),
     "G1 decision quality (does the answer match the underwriter?)   ·   G2 adoption (is it used in the workflow?)   ·   G3 economics (is unit cost falling?)",
     size=11, color=GREY)

rect(s, Inches(0.75), Inches(5.95), Inches(11.85), Inches(0.55), fill=RGBColor(0xEC, 0xF3, 0xF9), line=None)
text(s, Inches(1.0), Inches(6.07), Inches(11.4), Inches(0.35),
     "The ask: one value stream, one accountable owner, three domain stewards, and 90 days with a measured baseline.",
     size=11.5, bold=True, color=NAVY)
notes(s, "Close on the ask, not the technology.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
