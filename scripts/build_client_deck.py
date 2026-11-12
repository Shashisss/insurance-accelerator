"""Client deck in the Insurance Knowledge Framework house style.

    python scripts/build_client_deck.py

Same palette, type and layout language as the single-page use-case deck
(F4F2FB cards, 5C10FF accent, E8F5F6 recommendation band, Aptos), so it reads as
the same family — with the story, the layer, the architecture and the outcomes.

Every number is taken from the running POC.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "files" / "Insurance_Knowledge_Framework_Client.pptx"

CARD = RGBColor(0xF4, 0xF2, 0xFB)
ACCENT = RGBColor(0x5C, 0x10, 0xFF)
BAND = RGBColor(0xE8, 0xF5, 0xF6)
INK = RGBColor(0x1E, 0x23, 0x40)
MUTED = RGBColor(0x5A, 0x61, 0x78)
HAIR = RGBColor(0xDE, 0xDB, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x11, 0x7A, 0x7A)

TITLE_FONT = "Aptos Display"
BODY_FONT = "Aptos"

W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


def _strip(shp):
    sp = shp._element
    style = sp.find(qn("p:style"))
    if style is not None:
        sp.remove(style)
    shp.shadow.inherit = False


def text(slide, x, y, w, h, value, size=12, bold=False, color=MUTED, align=PP_ALIGN.LEFT,
         font=BODY_FONT, spacing=1.0, anchor=MSO_ANCHOR.TOP, space_after=0):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(value.split("\n")):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        if space_after:
            para.space_after = Pt(space_after)
        run = para.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def card(slide, x, y, w, h, fill=CARD, line=None, radius=0.04):
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


def chip(slide, x, y, d, value, size=11):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, d, d)
    _strip(shp)
    shp.fill.solid()
    shp.fill.fore_color.rgb = ACCENT
    shp.line.fill.background()
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = str(value)
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = BODY_FONT


def frame(slide, kicker, title, subtitle=None, page=None, footer="Client proposition"):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    _strip(bg)
    bg.fill.solid()
    bg.fill.fore_color.rgb = WHITE
    bg.line.fill.background()
    slide.shapes._spTree.remove(bg._element)
    slide.shapes._spTree.insert(2, bg._element)

    text(slide, Inches(0.55), Inches(0.42), Inches(11), Inches(0.28), kicker.upper(), size=10, bold=True, color=ACCENT)
    text(slide, Inches(0.55), Inches(0.72), Inches(12.0), Inches(0.62), title, size=27, bold=True, color=INK, font=TITLE_FONT)
    if subtitle:
        text(slide, Inches(0.55), Inches(1.33), Inches(12.1), Inches(0.5), subtitle, size=11.5, color=MUTED, spacing=1.1)

    text(slide, Inches(0.55), Inches(7.06), Inches(10), Inches(0.25),
         f"Visionet  |  Insurance Knowledge Framework  |  {footer}", size=8, color=MUTED)
    if page is not None:
        rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.72), Inches(6.98), Inches(0.32), Inches(0.32))
        _strip(rect)
        rect.fill.solid()
        rect.fill.fore_color.rgb = ACCENT
        rect.line.fill.background()
        tf = rect.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = str(page)
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.color.rgb = WHITE
        run.font.name = BODY_FONT


def band(slide, y, height, label, statement, x=Inches(0.55), w=Inches(12.2)):
    card(slide, x, y, w, height, fill=BAND)
    text(slide, x + Inches(0.25), y + Inches(0.14), w - Inches(0.5), Inches(0.24), label.upper(),
         size=8.5, bold=True, color=TEAL)
    text(slide, x + Inches(0.25), y + Inches(0.4), w - Inches(0.55), height - Inches(0.5),
         statement, size=10.5, color=INK, spacing=1.12)


def three_cards(slide, items, y=Inches(2.55), h=Inches(2.72), x0=Inches(0.55), total_w=Inches(12.2), gap=Inches(0.22)):
    w = (total_w - gap * 2) / 3
    x = x0
    for num, head, sub, lines in items:
        card(slide, x, y, w, h)
        chip(slide, x + Inches(0.22), y + Inches(0.2), Inches(0.34), num)
        text(slide, x + Inches(0.66), y + Inches(0.24), w - Inches(0.85), Inches(0.3), head, size=9.5, bold=True, color=INK)
        text(slide, x + Inches(0.22), y + Inches(0.66), w - Inches(0.45), Inches(0.5), sub, size=12, bold=True, color=ACCENT, font=TITLE_FONT)
        body = "\n".join(lines)
        text(slide, x + Inches(0.22), y + Inches(1.16), w - Inches(0.45), h - Inches(1.3), body, size=9.5, color=MUTED, spacing=1.18)
        x += w + gap


def table(slide, headers, rows, x, y, w, h, ratios=None, size=9.5, head_size=9.5):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, h)
    tbl = shape.table
    if ratios:
        total = sum(ratios)
        for i, r in enumerate(ratios):
            tbl.columns[i].width = Emu(int(w * r / total))
    for j, head in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.text = head
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(head_size)
                run.font.bold = True
                run.font.color.rgb = INK
                run.font.name = BODY_FONT
        cell.margin_left = Inches(0.09)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xFB, 0xFA, 0xFE)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(size)
                    run.font.color.rgb = MUTED if j else INK
                    run.font.name = BODY_FONT
                    run.font.bold = j == 0
            cell.margin_left = Inches(0.09)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)


def notes(slide, value: str):
    slide.notes_slide.notes_text_frame.text = value


def chevron(slide, x, y, size=Inches(0.26), color=ACCENT):
    shp = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, x, y, size, size)
    _strip(shp)
    shp.rotation = 90
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()


# ==========================================================================
# 1 — title
# ==========================================================================
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
_strip(bg)
bg.fill.solid()
bg.fill.fore_color.rgb = WHITE
bg.line.fill.background()

card(s, Inches(0), Inches(0), W, Inches(0.09), fill=ACCENT, radius=0)
text(s, Inches(0.8), Inches(1.15), Inches(11), Inches(0.3), "INSURANCE KNOWLEDGE FRAMEWORK  |  PROPOSITION",
     size=10.5, bold=True, color=ACCENT)
text(s, Inches(0.8), Inches(1.55), Inches(11.4), Inches(1.7), "From records\nto reasoning", size=46, bold=True,
     color=INK, font=TITLE_FONT, spacing=0.95)
text(s, Inches(0.8), Inches(3.45), Inches(10.6), Inches(0.9),
     "A semantic and contextual layer that gives AI meaning, precedence and authority —\n"
     "proven on three insurance decisions, built to extend.",
     size=14, color=MUTED, spacing=1.25)
card(s, Inches(0.8), Inches(4.55), Inches(11.6), Inches(1.34), fill=CARD)
text(s, Inches(1.05), Inches(4.75), Inches(3.2), Inches(0.9), "3 decisions", size=17, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(1.05), Inches(5.12), Inches(3.2), Inches(0.4), "fleet renewal · reserving · pricing", size=9.5, color=MUTED)
text(s, Inches(4.35), Inches(4.75), Inches(3.2), Inches(0.9), "6 entities", size=17, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(4.35), Inches(5.12), Inches(3.2), Inches(0.4), "7 typed relationships, time on the edges", size=9.5, color=MUTED)
text(s, Inches(7.65), Inches(4.75), Inches(3.4), Inches(0.9), "82 tests", size=17, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(7.65), Inches(5.12), Inches(4.2), Inches(0.4), "running today, not slideware", size=9.5, color=MUTED)
text(s, Inches(0.8), Inches(6.55), Inches(11), Inches(0.3),
     "Visionet  |  Insurance Knowledge Framework  |  Client proposition  ·  v1.0  ·  Illustrative scenarios, not underwriting policy",
     size=8, color=MUTED)

# ==========================================================================
# 2 — the story
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The story", "AI does not fail on models. It fails on meaning.",
      "A customer journey crosses six systems. Each is authoritative for something different — and none of them can answer the question alone.", 2)

three_cards(s, [
    ("1", "FRAGMENTED", "Four truths, one customer",
     ["Policy admin says the property is covered.",
      "Claims says the loss is reserved.",
      "Billing says the premium is unpaid.",
      "Underwriting says the risk was declined.",
      "A human reconciles this by instinct. An agent cannot."]),
    ("2", "MEANING", "One model, with time on it",
     ["Canonical entities, one key each.",
      "Typed relationships that carry direction, meaning and dates.",
      "A vehicle that moves between policies still has one history.",
      "Meaning is encoded once, not re-derived in every report."]),
    ("3", "DECISION", "Evidence, not just a number",
     ["Rules read the model, not a spreadsheet.",
      "Every point shows the attribute, the threshold and the reason.",
      "Every recommendation names the person who decides.",
      "Same input, same answer, every time."]),
])
band(s, Inches(5.55), Inches(0.95), "The gap",
     "It is not data volume. It is meaning, precedence and authority — and today those live in people's heads. "
     "That is exactly what an agent cannot inherit.")
notes(s, "Open here. The failure mode is not the model; it is that four systems each tell a true, partial story.")

# ==========================================================================
# 3 — the use case, in their layout
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Use case  ·  fleet renewal", "Context-aware risk assessment at renewal",
      "Three governed metrics + two rules + historical exposure relationships + lifecycle impact across applications.", 3)

# scenario band
card(s, Inches(0.55), Inches(1.92), Inches(12.2), Inches(0.92))
text(s, Inches(0.78), Inches(2.04), Inches(2.4), Inches(0.24), "BUSINESS SCENARIO", size=8, bold=True, color=ACCENT)
text(s, Inches(0.78), Inches(2.28), Inches(2.5), Inches(0.5), "ABC Express renews P205\n40 vehicles transferred", size=9.5, color=INK, spacing=1.15)

steps = [
    ("2025  •  BEFORE RESTRUCTURING", "100 vehicles"),
    ("2026  •  TWO ENTITIES", "90 + 60 vehicles"),
    ("P205  •  JAN 2027", "60-vehicle fleet renewal"),
]
sx = Inches(3.35)
for head, value in steps:
    card(s, sx, Inches(2.0), Inches(2.85), Inches(0.62), fill=WHITE)
    text(s, sx + Inches(0.14), Inches(2.06), Inches(2.6), Inches(0.2), head, size=7.5, color=MUTED)
    text(s, sx + Inches(0.14), Inches(2.24), Inches(2.6), Inches(0.3), value, size=11.5, bold=True, color=INK)
    sx += Inches(3.02)

three_cards(s, [
    ("1", "ONTOLOGY", "Connects changing exposures",
     ["Group: 150 vehicles / 2 entities",
      "P205: 60 vehicles; 40 transferred",
      "V041 → P101 → ₹5L prior claim",
      "Time-valid policy / vehicle links"]),
    ("2", "CONTEXT & RULES", "Selects applicable rules",
     ["High-risk fleet; renewal Jan 2027",
      "R1: loss ratio ≥60% → refer",
      "R2: group >120 → group review",
      "V041 history = supporting evidence"]),
    ("3", "SEMANTIC & LIFECYCLE", "Three metrics; one change",
     ["Loss ratio: 60% (v2 incl. ALAE)",
      "Frequency: 13.3 / 100 veh-years",
      "Severity: ₹30k / claim",
      "v1 → v2: 50% → 60%; trace impact"]),
], y=Inches(3.0), h=Inches(2.35))

band(s, Inches(5.55), Inches(0.82), "Recommendation",
     "Refer P205 for senior review; group assessment required. The underwriter retains the final decision.")
text(s, Inches(0.55), Inches(6.55), Inches(11.5), Inches(0.3),
     "BUSINESS FUNCTIONS   Underwriting · Actuarial · Claims · Risk Management · BI / Analytics",
     size=8, bold=True, color=INK)

# ==========================================================================
# 4 — the semantic and contextual layer
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The layer", "A runtime contract, not a glossary",
      "Five capabilities that machines and people both consume. The ontology defines meaning; context decides which meaning applies to this question.", 4)

caps = [
    ("1", "CANONICAL ENTITIES", "Customer · Policy · Property ·\nVehicle · Coverage · Claim", "One name, one key, one owner. No system redefines them."),
    ("2", "RELATIONSHIPS", "Covers · owns · arisesFrom ·\nservicedBy", "Typed and directed — and dated, so a transfer has a before and after."),
    ("3", "TAXONOMIES", "Loss causes, coverage classes,\noccupancy, decline reasons", "The vocabulary a model can reason over, controlled."),
    ("4", "CONSTRAINTS & INFERENCE", "Validation, referential integrity,\nhard stops", "What must be true; what may be inferred; what must never be assumed."),
    ("5", "CONTEXT & AUTHORITY", "Who is asking, at what date,\nwith what permission", "Same data, different permitted answer for underwriter, adjuster, auditor."),
]
cx = Inches(0.55)
cw = Inches(2.28)
for num, head, mid, foot in caps:
    card(s, cx, Inches(2.05), cw, Inches(2.95))
    chip(s, cx + Inches(0.16), Inches(2.19), Inches(0.3), num, size=9)
    text(s, cx + Inches(0.54), Inches(2.24), cw - Inches(0.68), Inches(0.42), head, size=7.8, bold=True, color=INK, spacing=1.0)
    text(s, cx + Inches(0.16), Inches(2.72), cw - Inches(0.32), Inches(0.75), mid, size=9, color=ACCENT, spacing=1.15)
    text(s, cx + Inches(0.16), Inches(3.55), cw - Inches(0.32), Inches(1.3), foot, size=8.8, color=MUTED, spacing=1.15)
    cx += cw + Inches(0.13)

band(s, Inches(5.2), Inches(0.95), "Context is the part everyone skips",
     "Read · Recommend · Commit — stated per role and per agent. Time is part of the context: ‘which fleet covered this vehicle at renewal’ "
     "is unanswerable without a dated edge, and so is ‘what did we believe in March’.")
text(s, Inches(0.55), Inches(6.3), Inches(11.6), Inches(0.4),
     "Two rules keep it honest:  a domain may publish its own data product, but may not redefine a canonical entity;  "
     "and a rule references a metric version, never a hard-coded number.",
     size=8.8, color=MUTED, spacing=1.1)

# ==========================================================================
# 5 — where it sits
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Architecture", "Where the layer sits",
      "Sources of record feed foundations; the semantic layer is the only place meaning lives; every experience — human or agent — reads through it.", 5)

# control plane strip
card(s, Inches(0.55), Inches(1.92), Inches(12.2), Inches(0.42), fill=WHITE, line=HAIR)
text(s, Inches(0.72), Inches(2.0), Inches(1.6), Inches(0.24), "CONTROL PLANE", size=7.5, bold=True, color=ACCENT)
text(s, Inches(2.3), Inches(2.0), Inches(10.2), Inches(0.24),
     "identity   ·   catalog   ·   lineage   ·   policy as code   ·   observability   ·   cost",
     size=8.5, color=MUTED)

cols = [
    (Inches(0.55), Inches(2.35), "SOURCES", WHITE, HAIR,
     ["Policy admin", "Claims", "Billing", "UW workbench", "Documents"]),
    (Inches(3.5), Inches(2.45), "DATA FOUNDATIONS", WHITE, HAIR,
     ["Bronze — raw, as-is", "Silver — typed, conformed", "Gold — domain data products", "Quality, lineage, history"]),
    (Inches(6.5), Inches(3.1), "SEMANTIC LAYER", CARD, ACCENT,
     ["Canonical entities", "Relationships, with time", "Metric layer (versioned)", "Rules service", "Evidence store"]),
    (Inches(10.05), Inches(2.7), "EXPERIENCE", WHITE, HAIR,
     ["Workbench", "API / tool surface", "Agent runtime", "BI & reporting"]),
]

for x, w, head, fill, line, items in cols:
    card(s, x, Inches(2.55), w, Inches(3.05), fill=fill, line=line)
    colour = ACCENT if head == "SEMANTIC LAYER" else INK
    text(s, x + Inches(0.18), Inches(2.7), w - Inches(0.36), Inches(0.24), head, size=8, bold=True, color=colour)
    cy = Inches(3.02)
    for item in items:
        text(s, x + Inches(0.18), cy, w - Inches(0.3), Inches(0.24), "·  " + item, size=8.6, color=MUTED)
        cy += Inches(0.42)

for x in (Inches(3.05), Inches(6.06), Inches(9.7)):
    chevron(s, x, Inches(3.95))

text(s, Inches(0.55), Inches(5.75), Inches(12.2), Inches(0.3),
     "RUNNING TODAY  ·  EVERYTHING SHOWN  ·  PRODUCTION SUBSTITUTES COMPONENTS, NOT THE MODEL",
     size=7.5, bold=True, color=INK)
text(s, Inches(0.55), Inches(6.0), Inches(12.2), Inches(0.75),
     "Today: CSV sources · in-memory graph · YAML ontology and metrics · Python rules service · FastAPI · Streamlit workbench.\n"
     "Production swaps components, not the model: lakehouse (Delta) · Neo4j Aura · governed catalog and metric layer · API management + identity · embedded in the UW and claims screens.",
     size=8.6, color=MUTED, spacing=1.2)

# ==========================================================================
# 6 — POC vs production
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Components", "Prove the model, replace the plumbing",
      "Replace one component at a time. The ontology, the metric definitions and the evidence contract stay stable.", 6)

rows = [
    ['Ontology repository', 'YAML in Git, one source of truth', 'Governed catalog, versioned releases', 'One definition, reviewable'],
    ['Graph store', 'In-memory traversal', 'Neo4j Aura or equivalent', 'Multi-hop reasoning at scale'],
    ['Lakehouse', 'Sample CSV book', 'Databricks / Fabric with Delta', 'History, lineage, isolation'],
    ['Rules & inference', 'Python, config-driven', 'Rules service + decision log', 'Auditability, replay by date'],
    ['Metric layer', 'YAML definitions', 'dbt / Unity Catalog metrics', 'Governed, reusable metrics'],
    ['API & identity', 'FastAPI, local', 'API management + Entra ID', 'Governed access per role'],
    ['Experience', 'Streamlit workbench', 'Embedded in UW / claims screens', 'Adoption inside the workflow'],
    ['Documents & vectors', 'Not in the POC', 'Extraction + governed embeddings', 'Unstructured evidence'],
]
table(s, ['Capability', 'POC today', 'Production option', 'Why it matters'], rows,
      Inches(0.55), Inches(1.95), Inches(12.2), Inches(4.5),
      ratios=[2.1, 2.9, 3.0, 3.0])

text(s, Inches(0.55), Inches(6.62), Inches(12.2), Inches(0.3),
     "What is already running: three decisions, 82 tests, an API, a workbench and an assistant that answers from tools — not from a model's memory.",
     size=8.6, color=MUTED)

# ==========================================================================
# 7 — business outcomes
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Business outcomes", "Where the value lands",
      "Four value streams share one spine. Each KPI is a hypothesis with a baseline, an owner and a measurement window — that is what a 90-day pilot buys.", 7)

rows = [
    ['Underwriting renewal', 'Policy-only view replaced by policy + group + transfer history', 'Referral pack time · referral precision'],
    ['Claims reserving', 'Adverse development decomposed into drivers, not asserted', 'Reserving cycle time · audit findings'],
    ['Pricing & adequacy', 'Indication recomputed from versioned assumptions, with sensitivity', 'Quote turnaround · rate adequacy at renewal'],
    ['Data onboarding', 'New source maps to canonical entities and validates without touching rules', 'Effort per new source'],
    ['Governance', 'One definition per metric, with an impact trace when it changes', 'Metric disputes · restatements'],
]
table(s, ['Value stream', 'What changes', 'KPI to baseline'], rows,
      Inches(0.55), Inches(2.0), Inches(12.2), Inches(3.4), ratios=[2.3, 6.0, 3.4])

band(s, Inches(5.62), Inches(0.92), "The honest part",
     "We are not quoting percentages yet. Each target is a hypothesis: baseline, owner, measurement window. "
     "The pilot's first job is to replace these words with numbers from your book.")

# ==========================================================================
# 8 — roadmap + ask
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Roadmap", "90 days to prove, three quarters to scale",
      "Start narrow, prove one decision, extend the same spine. The model does not change as the scope grows.", 8)

phases = [
    ("0–90 DAYS", "Prove", ["One value stream, one owner", "Six entities, ruleset v1.0", "Workbench + explained API", "Baseline metrics, 82 tests"]),
    ("Q2", "Pilot", ["Add claims and billing sources", "Three domains, 10× data", "Governed ontology repository", "Metric layer + lineage"]),
    ("Q3–Q4", "Scale", ["ACORD-aligned extensions", "Agent tools with authority", "Policy engine + audit trail", "Unit economics and FinOps"]),
]
x = Inches(0.55)
for period, name, items in phases:
    card(s, x, Inches(1.98), Inches(3.9), Inches(3.25))
    text(s, x + Inches(0.24), Inches(2.14), Inches(3.4), Inches(0.22), period, size=7.5, bold=True, color=ACCENT)
    text(s, x + Inches(0.24), Inches(2.38), Inches(3.4), Inches(0.4), name, size=17, bold=True, color=INK, font=TITLE_FONT)
    cy = Inches(2.9)
    for item in items:
        text(s, x + Inches(0.24), cy, Inches(3.45), Inches(0.5), "—  " + item, size=9, color=MUTED, spacing=1.05)
        cy += Inches(0.55)
    x += Inches(4.15)

text(s, Inches(0.55), Inches(5.42), Inches(12.2), Inches(0.24), "GATES", size=7.5, bold=True, color=ACCENT)
text(s, Inches(0.55), Inches(5.66), Inches(12.2), Inches(0.3),
     "G1  decision quality — does the answer match the underwriter?      G2  adoption — is it used inside the workflow?      G3  economics — is unit cost falling?",
     size=8.8, color=MUTED)

band(s, Inches(6.1), Inches(0.78), "The ask",
     "One value stream, one accountable owner, three domain stewards — and 90 days against a measured baseline.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
