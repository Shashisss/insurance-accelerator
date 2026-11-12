"""Client deck — visual edition, same house style.

    python scripts/build_client_deck.py

Palette and type as the use-case deck (F4F2FB cards, 5C10FF accent, E8F5F6 band,
Aptos, body 11pt+), but the argument is carried by shapes and numbers rather
than paragraphs: a before/after picture, a chevron timeline, an architecture
diagram, a paired stack, tiles.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "files" / "Insurance_Knowledge_Framework_Client.pptx"

CARD = RGBColor(0xF4, 0xF2, 0xFB)
ACCENT = RGBColor(0x5C, 0x10, 0xFF)
ACCENT_SOFT = RGBColor(0xEA, 0xE2, 0xFF)
BAND = RGBColor(0xE8, 0xF5, 0xF6)
INK = RGBColor(0x1E, 0x23, 0x40)
MUTED = RGBColor(0x4E, 0x55, 0x6B)
HAIR = RGBColor(0xDE, 0xDB, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0F, 0x6E, 0x6E)
GREY_SOFT = RGBColor(0xEC, 0xEC, 0xF2)

TITLE_FONT = "Aptos Display"
BODY_FONT = "Aptos"

W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def _strip(shp):
    sp = shp._element
    style = sp.find(qn("p:style"))
    if style is not None:
        sp.remove(style)
    shp.shadow.inherit = False


def text(slide, x, y, w, h, value, size=11, bold=False, color=MUTED, align=PP_ALIGN.LEFT,
         font=BODY_FONT, spacing=1.0, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(value.split("\n")):
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


def shape(slide, kind, x, y, w, h, fill=None, line=None, line_w=1.0, text_value=None,
          font_size=11, font_color=WHITE, bold=True, rotation=0):
    shp = slide.shapes.add_shape(kind, x, y, w, h)
    _strip(shp)
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
    if rotation:
        shp.rotation = rotation
    if text_value is not None:
        tf = shp.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = text_value
        r.font.size = Pt(font_size)
        r.font.bold = bold
        r.font.color.rgb = font_color
        r.font.name = BODY_FONT
    return shp


def card(slide, x, y, w, h, fill=CARD, line=None, radius=0.05):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, line=line, rotation=0) if False else _card(slide, x, y, w, h, fill, line, radius)


def _card(slide, x, y, w, h, fill, line, radius):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    _strip(shp)
    shp.adjustments[0] = radius
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    return shp


def frame(slide, kicker, title, subtitle=None, page=None, dark=False):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    _strip(bg)
    bg.fill.solid()
    bg.fill.fore_color.rgb = WHITE
    bg.line.fill.background()
    slide.shapes._spTree.remove(bg._element)
    slide.shapes._spTree.insert(2, bg._element)

    text(slide, Inches(0.55), Inches(0.40), Inches(11), Inches(0.28), kicker.upper(), size=10.5, bold=True, color=ACCENT)
    size = 27 if len(title) <= 50 else 24 if len(title) <= 58 else 22
    text(slide, Inches(0.55), Inches(0.70), Inches(12.1), Inches(0.6), title, size=size, bold=True, color=INK, font=TITLE_FONT)
    if subtitle:
        text(slide, Inches(0.55), Inches(1.30), Inches(12.2), Inches(0.5), subtitle, size=11.5, color=MUTED, spacing=1.15)

    text(slide, Inches(0.55), Inches(7.08), Inches(9.5), Inches(0.25),
         "Visionet  |  Insurance Knowledge Framework  |  Client proposition", size=9.5, color=MUTED)
    if page is not None:
        shape(slide, MSO_SHAPE.RECTANGLE, Inches(12.72), Inches(7.00), Inches(0.32), Inches(0.32),
              fill=ACCENT, text_value=str(page), font_size=10)


def band(slide, y, height, label, statement, x=Inches(0.55), w=Inches(12.2)):
    card(slide, x, y, w, height, fill=BAND)
    text(slide, x + Inches(0.25), y + Inches(0.12), w - Inches(0.5), Inches(0.24), label.upper(),
         size=9.5, bold=True, color=TEAL)
    text(slide, x + Inches(0.25), y + Inches(0.38), w - Inches(0.55), height - Inches(0.46),
         statement, size=11, color=INK, spacing=1.15)


def icon(slide, kind, x, y, d, fill=ACCENT, inner=None, inner_color=WHITE):
    shape(slide, kind, x, y, d, d, fill=fill)
    if inner:
        pad = d * 0.3
        text(slide, x + pad, y + pad * 0.85, d - 2 * pad, d - pad, inner, size=11, bold=True,
             color=inner_color, align=PP_ALIGN.CENTER)


def chevron(slide, x, y, w, h, fill, label, size=11, color=WHITE):
    shp = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, x, y, w, h)
    _strip(shp)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    tf = shp.text_frame
    tf.margin_left = Inches(0.12)
    tf.margin_right = Inches(0.05)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = color
    r.font.name = BODY_FONT


def connector(slide, x1, y1, x2, y2, color=ACCENT, width=1.5, dash=False):
    from pptx.enum.shapes import MSO_CONNECTOR

    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    if dash:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE

        conn.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return conn


def notes(slide, value: str):
    slide.notes_slide.notes_text_frame.text = value


# ==========================================================================
# 1 — title with a visual
# ==========================================================================
s = prs.slides.add_slide(BLANK)
card(s, Inches(0), Inches(0), W, Inches(0.10), fill=ACCENT, radius=0)
text(s, Inches(0.8), Inches(1.05), Inches(11), Inches(0.3), "INSURANCE KNOWLEDGE FRAMEWORK  |  PROPOSITION",
     size=11, bold=True, color=ACCENT)
text(s, Inches(0.8), Inches(1.45), Inches(7.4), Inches(1.8), "From records\nto reasoning", size=50, bold=True,
     color=INK, font=TITLE_FONT, spacing=0.92)
text(s, Inches(0.8), Inches(3.55), Inches(6.2), Inches(0.9),
     "A semantic and contextual layer that gives AI\nmeaning, precedence and authority.",
     size=14, color=MUTED, spacing=1.35)

# right: fragmented systems -> one connected model
fx = Inches(7.75)
systems = ["Policy admin", "Claims", "Billing", "UW desk"]
for i, name in enumerate(systems):
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, fx, Inches(1.62) + i * Inches(0.60), Inches(1.55), Inches(0.40),
          fill=GREY_SOFT)
    text(s, fx + Inches(0.12), Inches(1.70) + i * Inches(0.60), Inches(1.35), Inches(0.24), name,
         size=9, color=MUTED)

shape(s, MSO_SHAPE.RIGHT_ARROW, Inches(9.55), Inches(2.62), Inches(0.55), Inches(0.34), fill=ACCENT)

cx, cy = Inches(11.35), Inches(2.78)
centre_r = Inches(0.42)
pts = [(-0.95, -0.85), (0.0, -1.10), (0.95, -0.85), (-0.95, 0.85), (0.0, 1.10), (0.95, 0.85)]
for dx, dy in pts:
    connector(s, cx, cy, cx + Inches(dx), cy + Inches(dy), color=RGBColor(0xC9, 0xB8, 0xFF), width=1.5)
for dx, dy in pts:
    px, py = cx + Inches(dx), cy + Inches(dy)
    shape(s, MSO_SHAPE.OVAL, px - Inches(0.15), py - Inches(0.15), Inches(0.30), Inches(0.30), fill=WHITE,
          line=ACCENT, line_w=1.5)
shape(s, MSO_SHAPE.OVAL, cx - centre_r, cy - centre_r, centre_r * 2, centre_r * 2, fill=ACCENT)

text(s, Inches(0.8), Inches(4.95), Inches(11.6), Inches(0.4),
     "3 decisions  ·  6 entities  ·  aligned to the OMG P&C model  ·  88 tests",
     size=13, bold=True, color=ACCENT)
text(s, Inches(0.8), Inches(6.55), Inches(11.6), Inches(0.3),
     "Visionet  |  Insurance Knowledge Framework  |  Client proposition  ·  v1.2  ·  Illustrative scenarios, not underwriting policy",
     size=9.5, color=MUTED)
notes(s, "The picture is the argument: four grey systems on the left, one connected model on the right.")

# ==========================================================================
# 2 — before / after
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The story", "AI does not fail on models. It fails on meaning.",
      "One customer, four systems, four true statements that don't add up.", 2)

# BEFORE panel
card(s, Inches(0.55), Inches(1.95), Inches(5.4), Inches(3.2), fill=WHITE, line=HAIR)
text(s, Inches(0.80), Inches(2.10), Inches(4.8), Inches(0.25), "TODAY  ·  FOUR SYSTEMS", size=9.5, bold=True, color=ACCENT)
rows = [("Policy admin", "Covered", RGBColor(0x2E, 0x9E, 0x5B)),
        ("Claims", "Reserved", RGBColor(0xD0, 0x8A, 0x1E)),
        ("Billing", "Unpaid", RGBColor(0xC0, 0x3A, 0x2B)),
        ("Underwriting", "Declined", RGBColor(0xC0, 0x3A, 0x2B))]
y = Inches(2.55)
for name, status, colour in rows:
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.80), y, Inches(3.0), Inches(0.42), fill=GREY_SOFT)
    text(s, Inches(0.95), y + Inches(0.10), Inches(2.0), Inches(0.25), name, size=10.5, color=MUTED)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3.95), y, Inches(1.75), Inches(0.42), fill=WHITE, line=colour)
    text(s, Inches(3.95), y + Inches(0.10), Inches(1.75), Inches(0.25), status, size=10.5, bold=True,
         color=colour, align=PP_ALIGN.CENTER)
    y += Inches(0.60)

shape(s, MSO_SHAPE.RIGHT_ARROW, Inches(6.12), Inches(3.35), Inches(0.85), Inches(0.45), fill=ACCENT)

# AFTER panel
card(s, Inches(7.15), Inches(1.95), Inches(5.6), Inches(3.2), fill=CARD)
text(s, Inches(7.40), Inches(2.10), Inches(5.0), Inches(0.25), "WITH THE LAYER  ·  ONE MODEL", size=9.5, bold=True, color=ACCENT)
# mini graph inside the card
gx, gy = Inches(9.95), Inches(3.55)
satellites = [("Policy", -1.55, -0.95), ("Coverage", 0.35, -0.95), ("Claim", -1.55, 0.55), ("Risk", 0.35, 0.55)]
for label, dx, dy in satellites:
    sx, sy = gx + Inches(dx), gy + Inches(dy)
    connector(s, gx, gy, sx + Inches(0.42), sy + Inches(0.16), color=RGBColor(0xC9, 0xB8, 0xFF))
for label, dx, dy in satellites:
    sx, sy = gx + Inches(dx), gy + Inches(dy)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, sx, sy, Inches(0.95), Inches(0.34), fill=WHITE, line=ACCENT)
    text(s, sx, sy + Inches(0.06), Inches(0.95), Inches(0.22), label, size=8.5, color=INK, align=PP_ALIGN.CENTER)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, gx - Inches(0.62), gy - Inches(0.26), Inches(1.24), Inches(0.52), fill=ACCENT)
text(s, gx - Inches(0.62), gy - Inches(0.11), Inches(1.24), Inches(0.25), "Property", size=9, bold=True,
     color=WHITE, align=PP_ALIGN.CENTER)
text(s, Inches(7.40), Inches(4.55), Inches(5.0), Inches(0.5), "One name, one key, one timeline — and the\nquestion can be answered once.", size=10.5, color=MUTED, spacing=1.2)

band(s, Inches(5.45), Inches(0.95), "The gap",
     "It is not data volume. It is meaning, precedence and authority — and today those live in people's heads, "
     "which is what an agent cannot inherit.")
notes(s, "Left panel: four systems, four true statements. Right panel: one model. The arrow is the whole product.")

# ==========================================================================
# 3 — the use case, timeline first
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Use case  ·  fleet renewal", "Context-aware risk assessment at renewal",
      "A truck moved between policies. The policy looks safer; the book doesn't.", 3)

# timeline chevrons
chevron(s, Inches(0.55), Inches(1.90), Inches(4.1), Inches(0.85), ACCENT_SOFT,
        "2025  ·  100 vehicles\non P205", size=11, color=INK)
chevron(s, Inches(4.55), Inches(1.90), Inches(4.1), Inches(0.85), RGBColor(0xC9, 0xB8, 0xFF),
        "2026  ·  split into 90 + 60\none group of 150", size=11, color=INK)
chevron(s, Inches(8.55), Inches(1.90), Inches(4.2), Inches(0.85), ACCENT,
        "JAN 2027  ·  P205 renews\nwith 60 vehicles", size=11, color=WHITE)

# three visual cards
cards = [
    ("ONTOLOGY", MSO_SHAPE.OVAL, ["150 vehicles, 2 entities", "40 transferred, V041 among them", "V041 carried a ₹5L claim"], "Time-valid links"),
    ("CONTEXT & RULES", MSO_SHAPE.DIAMOND, ["R1: loss ratio ≥60% → refer", "R2: group >120 → group review", "V041 history = evidence only"], "Rules read the model"),
    ("SEMANTIC & LIFECYCLE", MSO_SHAPE.HEXAGON, ["Loss ratio 60% (v2, +ALAE)", "Frequency 13.3 / 100 veh-yr", "Severity ₹30k / claim"], "v1 → v2 moves 2 of 2"),
]
x = Inches(0.55)
for head, kind, lines, footer in cards:
    card(s, x, Inches(3.02), Inches(3.9), Inches(2.25))
    shape(s, kind, x + Inches(0.24), Inches(3.22), Inches(0.34), Inches(0.34), fill=ACCENT)
    text(s, x + Inches(0.72), Inches(3.24), Inches(3.0), Inches(0.3), head, size=9.5, bold=True, color=INK)
    text(s, x + Inches(0.24), Inches(3.75), Inches(3.45), Inches(0.9), "\n".join(lines), size=11, color=MUTED, spacing=1.25)
    text(s, x + Inches(0.24), Inches(4.78), Inches(3.45), Inches(0.3), footer, size=10, bold=True, color=ACCENT)
    x += Inches(4.13)

band(s, Inches(5.50), Inches(0.85), "Recommendation",
     "Refer P205 for senior review; group assessment required. The underwriter retains the final decision.")

# ==========================================================================
# 4 — five capabilities as tiles
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The layer", "Five capabilities, one contract",
      "Machines and people consume the same definitions — that is what makes an answer reproducible.", 4)

tiles = [
    ("ENTITIES", MSO_SHAPE.OVAL, "Customer, Policy,\nProperty, Vehicle,\nCoverage, Claim"),
    ("RELATIONSHIPS", MSO_SHAPE.DIAMOND, "Covers, owns,\narisesFrom — typed\nand dated"),
    ("TAXONOMIES", MSO_SHAPE.RECTANGLE, "Loss causes,\noccupancy,\ncoverage class"),
    ("CONSTRAINTS", MSO_SHAPE.ISOSCELES_TRIANGLE, "Required, keys,\nintegrity,\nhard stops"),
    ("CONTEXT", MSO_SHAPE.HEXAGON, "Who asks, as at\nwhen — read,\nrecommend, commit"),
]
x = Inches(0.55)
for head, kind, body in tiles:
    card(s, x, Inches(1.95), Inches(2.32), Inches(3.15))
    shape(s, kind, x + Inches(0.90), Inches(2.20), Inches(0.55), Inches(0.55), fill=ACCENT)
    text(s, x + Inches(0.15), Inches(3.00), Inches(2.02), Inches(0.3), head, size=9.5, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.15), Inches(3.40), Inches(2.02), Inches(1.2), body, size=11, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.25)
    x += Inches(2.42)

band(s, Inches(5.40), Inches(1.0), "Context is the part everyone skips",
     "Read · Recommend · Commit, stated per role and per agent. Time is context too: ‘which fleet covered this vehicle "
     "at renewal’ is unanswerable without a dated edge.")

# ==========================================================================
# 5 — standards, as three columns of chips
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Standards", "Standards give vocabulary, not volume",
      "A choice, an obligation and a market condition — read the three columns that way.", 5)

cols = [
    ("CONTENT MODELS", ["OMG P&C  ·  used here", "ACORD  ·  member only", "riskine  ·  Apache-2.0", "FIBO  ·  legal entities"], True),
    ("REPORTING", ["Solvency II XBRL", "IFRS 17 taxonomy", "NAIC statutory blanks"], False),
    ("INTEROPERABILITY", ["OPIN  ·  Open Insurance Brasil", "EU FiDA", "UK Open Finance", "ISO 20022"], False),
]
x = Inches(0.55)
for head, items, chosen in cols:
    card(s, x, Inches(1.95), Inches(3.9), Inches(3.45), fill=CARD if chosen else WHITE, line=None if chosen else HAIR)
    text(s, x + Inches(0.24), Inches(2.10), Inches(3.4), Inches(0.25), head, size=9.5, bold=True, color=ACCENT)
    cy = Inches(2.55)
    for item in items:
        used = item.endswith("used here")
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x + Inches(0.24), cy, Inches(3.42), Inches(0.44),
              fill=ACCENT if used else GREY_SOFT)
        text(s, x + Inches(0.36), cy + Inches(0.11), Inches(3.2), Inches(0.24), item,
             size=10.5, bold=used, color=WHITE if used else MUTED)
        cy += Inches(0.56)
    x += Inches(4.13)

band(s, Inches(5.62), Inches(1.05), "What we did",
     "Customer → party, Policy → policy, Property → insurable_object, Coverage → coverage, Claim → claim — "
     "verified against the model's 256 tables. We use five, deliberately.")

# ==========================================================================
# 6 — architecture, diagram-first
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Architecture", "Where the layer sits",
      "Everything reads through the middle column. Nothing reads system to system.", 6)

card(s, Inches(0.55), Inches(1.88), Inches(12.2), Inches(0.42), fill=WHITE, line=HAIR)
text(s, Inches(0.75), Inches(1.96), Inches(2.0), Inches(0.24), "CONTROL PLANE", size=9, bold=True, color=ACCENT)
text(s, Inches(2.45), Inches(1.96), Inches(10.0), Inches(0.24),
     "identity · catalog · lineage · policy as code · observability", size=10, color=MUTED)

blocks = [
    (Inches(0.55), Inches(2.3), "SOURCES", WHITE, HAIR, ["Policy admin", "Claims", "Billing", "UW desk", "Documents"]),
    (Inches(3.55), Inches(2.4), "FOUNDATIONS", WHITE, HAIR, ["Bronze — raw", "Silver — conformed", "Gold — marts", "Lineage"]),
    (Inches(6.65), Inches(3.0), "SEMANTIC LAYER", ACCENT_SOFT, ACCENT, ["Entities", "Edges, with time", "Metrics, versioned", "Rules service", "Evidence store"]),
    (Inches(10.05), Inches(2.7), "EXPERIENCE", WHITE, HAIR, ["Workbench", "API / tools", "Agent runtime", "BI"]),
]
for x, w, head, fill, line, items in blocks:
    card(s, x, Inches(2.5), w, Inches(3.15), fill=fill, line=line)
    text(s, x + Inches(0.18), Inches(2.62), w - Inches(0.36), Inches(0.24), head, size=9, bold=True,
         color=ACCENT if head == "SEMANTIC LAYER" else INK)
    cy = Inches(3.02)
    for item in items:
        text(s, x + Inches(0.18), cy, w - Inches(0.3), Inches(0.24), "·  " + item, size=10.5, color=MUTED)
        cy += Inches(0.44)

for x in (Inches(2.95), Inches(6.05), Inches(9.75)):
    shape(s, MSO_SHAPE.RIGHT_ARROW, x, Inches(3.85), Inches(0.45), Inches(0.32), fill=ACCENT)

text(s, Inches(0.55), Inches(5.85), Inches(12.2), Inches(0.9),
     "Today: CSVs · in-memory graph · YAML ontology and metrics · Python rules · FastAPI · Streamlit.\n"
     "Production swaps components, not the model: Delta lakehouse · Neo4j Aura · governed catalogue · API management.",
     size=10, color=MUTED, spacing=1.3)

# ==========================================================================
# 7 — inside the semantic layer
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Inside the layer", "What sits inside — and where the AI is allowed to stand",
      "Definitions on the left, evidence on the right. The graph holds the facts, the trace holds the reasoning.", 7)

# sources
card(s, Inches(0.55), Inches(2.05), Inches(2.1), Inches(3.2), fill=WHITE, line=HAIR)
text(s, Inches(0.72), Inches(2.18), Inches(1.8), Inches(0.25), "SOURCES", size=9, bold=True, color=MUTED)
for i, name in enumerate(["Policy admin", "Claims", "Billing", "UW desk", "Documents"]):
    text(s, Inches(0.72), Inches(2.52) + i * Inches(0.5), Inches(1.85), Inches(0.3), "·  " + name, size=10, color=MUTED)

shape(s, MSO_SHAPE.RIGHT_ARROW, Inches(2.75), Inches(3.45), Inches(0.4), Inches(0.3), fill=ACCENT)
text(s, Inches(2.30), Inches(3.85), Inches(1.35), Inches(0.4), "map +\nvalidate", size=8, color=MUTED, align=PP_ALIGN.CENTER)

# the layer container
card(s, Inches(3.25), Inches(1.95), Inches(6.6), Inches(3.45), fill=CARD, line=ACCENT)
text(s, Inches(3.45), Inches(2.05), Inches(4.0), Inches(0.25), "SEMANTIC LAYER", size=9.5, bold=True, color=ACCENT)

inner = [
    ("Ontology repo", "party · policy · cover · claim", 3.45, 2.40),
    ("Graph store", "dated cover edges, claim links", 5.55, 2.40),
    ("Metric layer", "loss ratio · frequency · severity", 7.65, 2.40),
    ("Rules service", "referral thresholds · hard stops", 3.45, 3.35),
    ("Evidence store", "decision + inputs + version", 5.55, 3.35),
    ("Tool surface", "assess · history · impact", 7.65, 3.35),
]
for name, sub, x, y in inner:
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(1.95), Inches(0.78),
          fill=WHITE, line=HAIR)
    text(s, Inches(x + 0.10), Inches(y + 0.10), Inches(1.75), Inches(0.25), name, size=10, bold=True, color=INK)
    text(s, Inches(x + 0.10), Inches(y + 0.38), Inches(1.75), Inches(0.35), sub, size=8.5, color=MUTED)

text(s, Inches(3.45), Inches(4.35), Inches(6.2), Inches(0.9),
     "History: every vehicle↔policy link is dated, so ‘which fleet covered this truck at renewal’ is a query, not a guess.\n"
     "Trace: each underwriting decision stores its inputs, findings and ruleset version — replayable by date.",
     size=10, color=MUTED, spacing=1.25)

shape(s, MSO_SHAPE.RIGHT_ARROW, Inches(9.95), Inches(3.45), Inches(0.4), Inches(0.3), fill=ACCENT)
text(s, Inches(9.85), Inches(3.80), Inches(0.6), Inches(0.25), "read", size=8, color=MUTED, align=PP_ALIGN.CENTER)

# consumers
card(s, Inches(10.45), Inches(2.05), Inches(2.3), Inches(1.9), fill=WHITE, line=HAIR)
text(s, Inches(10.62), Inches(2.18), Inches(2.0), Inches(0.25), "CONSUMERS", size=9, bold=True, color=MUTED)
for i, name in enumerate(["Workbench", "API", "BI"]):
    text(s, Inches(10.62), Inches(2.52) + i * Inches(0.5), Inches(2.0), Inches(0.3), "·  " + name, size=10, color=MUTED)

# AI band
card(s, Inches(10.45), Inches(4.05), Inches(2.3), Inches(1.35), fill=ACCENT)
text(s, Inches(10.62), Inches(4.18), Inches(2.0), Inches(0.25), "AI / AGENT", size=9, bold=True, color=WHITE)
text(s, Inches(10.62), Inches(4.45), Inches(2.0), Inches(0.85),
     "FNOL triage · renewal note\nexplain the decision\nnever computes", size=9, color=WHITE, spacing=1.2)

band(s, Inches(5.75), Inches(0.95), "The boundary",
     "In an insurer, the agent sits outside the layer: it can draft an FNOL summary, explain a referral or a reserve movement — "
     "but every figure it quotes came from the policy, claim and metric services, never from the model.")

# ==========================================================================
# 7 — paired stack, not a table
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Components", "Prove the model, replace the plumbing",
      "Six components, swapped one at a time. The ontology and the evidence contract stay put.", 7)

pairs = [
    ("Ontology repo", "YAML in Git", "Governed catalog"),
    ("Graph store", "In-memory", "Neo4j Aura"),
    ("Lakehouse", "Sample CSVs", "Delta on Fabric"),
    ("Rules", "Python service", "Rules + decision log"),
    ("API & identity", "FastAPI, local", "APIM + Entra ID"),
    ("Experience", "Streamlit", "Embedded in UW screen"),
]
text(s, Inches(0.55), Inches(1.90), Inches(4.9), Inches(0.25), "POC TODAY", size=9.5, bold=True, color=MUTED)
text(s, Inches(7.55), Inches(1.90), Inches(4.9), Inches(0.25), "PRODUCTION", size=9.5, bold=True, color=ACCENT)

cy = Inches(2.35)
for name, ours, theirs in pairs:
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.55), cy, Inches(4.9), Inches(0.52), fill=GREY_SOFT)
    text(s, Inches(0.75), cy + Inches(0.05), Inches(2.0), Inches(0.24), name, size=9, color=MUTED)
    text(s, Inches(0.75), cy + Inches(0.24), Inches(4.4), Inches(0.24), ours, size=11, color=INK)
    shape(s, MSO_SHAPE.RIGHT_ARROW, Inches(5.65), cy + Inches(0.10), Inches(0.6), Inches(0.32), fill=ACCENT)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.45), cy, Inches(3.4), Inches(0.52), fill=WHITE, line=ACCENT)
    text(s, Inches(6.65), cy + Inches(0.14), Inches(3.0), Inches(0.24), theirs, size=11, bold=True, color=ACCENT)
    cy += Inches(0.64)

text(s, Inches(10.15), Inches(2.35), Inches(2.6), Inches(3.4),
     "Same six entities.\nSame rules.\nSame evidence.\n\nA new store, a new\ncluster — not a\nnew model.",
     size=11, color=MUTED, spacing=1.35)

# ==========================================================================
# 9 — business outcomes, generic
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Business outcomes", "Where the value lands in an insurer",
      "Five moments where a decision is made — and where the layer changes what is possible.", 9)

outcomes = [
    ("RENEWAL", MSO_SHAPE.OVAL, "Policy + group + transfer\nhistory on one screen", "pack in minutes, not days"),
    ("FNOL", MSO_SHAPE.DIAMOND, "Coverage, prior losses and\ngaps at first notification", "triage, not re-keying"),
    ("RESERVING", MSO_SHAPE.RECTANGLE, "Adverse development\nbroken into drivers", "20 → 23 Cr, explained"),
    ("PRICING", MSO_SHAPE.ISOSCELES_TRIANGLE, "Indication from versioned\nassumptions, with sensitivity", "10L → 12.79L indicated"),
    ("ONBOARDING", MSO_SHAPE.HEXAGON, "New scheme or bordereaux\nmaps to canonical entities", "16 columns, one mapping"),
]
x = Inches(0.55)
for head, kind, body, example in outcomes:
    card(s, x, Inches(1.95), Inches(2.32), Inches(2.95))
    shape(s, kind, x + Inches(0.90), Inches(2.18), Inches(0.55), Inches(0.55), fill=ACCENT)
    text(s, x + Inches(0.15), Inches(2.95), Inches(2.02), Inches(0.25), head, size=9.5, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.15), Inches(3.28), Inches(2.02), Inches(0.8), body, size=10.5, color=INK, align=PP_ALIGN.CENTER, spacing=1.25)
    text(s, x + Inches(0.15), Inches(4.12), Inches(2.02), Inches(0.5), example, size=8.5, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.15)
    x += Inches(2.42)

band(s, Inches(5.15), Inches(0.95), "The honest part",
     "No percentages here. Each outcome needs a baseline, an owner and a measurement window on your book — that is what a 90-day pilot buys.")

# ==========================================================================
# 9 — roadmap as a timeline
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Roadmap", "90 days to prove, three quarters to scale",
      "One value stream first. The spine doesn't change as scope grows.", 10)

phases = [
    ("0–90 DAYS", "Prove", ["one use case", "six entities", "88 tests"], ACCENT),
    ("Q2", "Pilot", ["three domains", "10× data", "governed repo"], RGBColor(0x8B, 0x5C, 0xFF)),
    ("Q3–Q4", "Scale", ["ACORD alignment", "agent authority", "unit economics"], RGBColor(0xC0, 0xA8, 0xFF)),
]
x = Inches(0.55)
for period, name, items, colour in phases:
    card(s, x, Inches(1.95), Inches(4.0), Inches(2.6), fill=WHITE, line=HAIR)
    shape(s, MSO_SHAPE.RECTANGLE, x, Inches(1.95), Inches(4.0), Inches(0.10), fill=colour)
    text(s, x + Inches(0.26), Inches(2.18), Inches(3.4), Inches(0.22), period, size=9.5, bold=True, color=colour)
    text(s, x + Inches(0.26), Inches(2.44), Inches(3.4), Inches(0.4), name, size=20, bold=True, color=INK, font=TITLE_FONT)
    text(s, x + Inches(0.26), Inches(3.05), Inches(3.4), Inches(1.1), "\n".join("·  " + i for i in items),
         size=11, color=MUTED, spacing=1.35)
    x += Inches(4.13)

# gates as markers
gy = Inches(4.85)
connector(s, Inches(0.55), gy + Inches(0.16), Inches(12.2), gy + Inches(0.16), color=HAIR, width=2)
for gx, label in [(Inches(2.35), "G1"), (Inches(6.45), "G2"), (Inches(10.55), "G3")]:
    shape(s, MSO_SHAPE.OVAL, gx, gy, Inches(0.32), Inches(0.32), fill=ACCENT)
text(s, Inches(1.55), Inches(5.28), Inches(2.6), Inches(0.3), "decision quality", size=9.5, color=MUTED)
text(s, Inches(5.85), Inches(5.28), Inches(2.6), Inches(0.3), "adoption in workflow", size=9.5, color=MUTED)
text(s, Inches(9.95), Inches(5.28), Inches(2.8), Inches(0.3), "unit economics", size=9.5, color=MUTED)

band(s, Inches(5.95), Inches(0.85), "The ask",
     "One value stream, one accountable owner, three domain stewards — and 90 days against a measured baseline.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
