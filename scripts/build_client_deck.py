"""Client deck in the Insurance Knowledge Framework house style — larger type.

    python scripts/build_client_deck.py

Palette and layout follow the use-case deck (F4F2FB cards, 5C10FF accent,
E8F5F6 recommendation band, Aptos). Body copy is 11pt minimum so it reads from
the back of a room; slides are trimmed to fit rather than shrunk to fit.

Nine slides: story · use case · the layer · standards · architecture ·
POC vs production · outcomes · roadmap · and the ask.
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
BAND = RGBColor(0xE8, 0xF5, 0xF6)
INK = RGBColor(0x1E, 0x23, 0x40)
MUTED = RGBColor(0x4E, 0x55, 0x6B)
HAIR = RGBColor(0xDE, 0xDB, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0F, 0x6E, 0x6E)

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


def frame(slide, kicker, title, subtitle=None, page=None):
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

    text(slide, Inches(0.55), Inches(7.06), Inches(9.5), Inches(0.25),
         "Visionet  |  Insurance Knowledge Framework  |  Client proposition", size=10, color=MUTED)
    if page is not None:
        rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.70), Inches(6.98), Inches(0.34), Inches(0.34))
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
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = WHITE
        run.font.name = BODY_FONT


def band(slide, y, height, label, statement, x=Inches(0.55), w=Inches(12.2)):
    card(slide, x, y, w, height, fill=BAND)
    text(slide, x + Inches(0.25), y + Inches(0.12), w - Inches(0.5), Inches(0.24), label.upper(),
         size=9.5, bold=True, color=TEAL)
    text(slide, x + Inches(0.25), y + Inches(0.38), w - Inches(0.55), height - Inches(0.46),
         statement, size=11, color=INK, spacing=1.15)


def three_cards(slide, items, y, h, x0=Inches(0.55), total_w=Inches(12.2), gap=Inches(0.22)):
    w = (total_w - gap * 2) / 3
    x = x0
    for num, head, sub, lines, foot_line in items:
        card(slide, x, y, w, h)
        chip(slide, x + Inches(0.22), y + Inches(0.18), Inches(0.36), num)
        text(slide, x + Inches(0.68), y + Inches(0.22), w - Inches(0.9), Inches(0.3), head, size=10, bold=True, color=INK)
        text(slide, x + Inches(0.22), y + Inches(0.62), w - Inches(0.45), Inches(0.4), sub, size=13, bold=True,
             color=ACCENT, font=TITLE_FONT)
        text(slide, x + Inches(0.22), y + Inches(1.12), w - Inches(0.45), h - Inches(1.75),
             "\n".join(lines), size=11, color=MUTED, spacing=1.2)
        text(slide, x + Inches(0.22), y + h - Inches(0.58), w - Inches(0.45), Inches(0.4),
             foot_line, size=10, color=ACCENT, spacing=1.1)
        x += w + gap


def table(slide, headers, rows, x, y, w, h, ratios=None, size=11):
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
                run.font.size = Pt(size)
                run.font.bold = True
                run.font.color.rgb = INK
                run.font.name = BODY_FONT
        cell.margin_left = Inches(0.09)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
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
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)


def chevron(slide, x, y, size=Inches(0.24), color=ACCENT):
    shp = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, x, y, size, size)
    _strip(shp)
    shp.rotation = 90
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()


def notes(slide, value: str):
    slide.notes_slide.notes_text_frame.text = value


# ==========================================================================
# 1 — title
# ==========================================================================
s = prs.slides.add_slide(BLANK)
card(s, Inches(0), Inches(0), W, Inches(0.09), fill=ACCENT, radius=0)
text(s, Inches(0.8), Inches(1.10), Inches(11), Inches(0.3), "INSURANCE KNOWLEDGE FRAMEWORK  |  PROPOSITION",
     size=11, bold=True, color=ACCENT)
text(s, Inches(0.8), Inches(1.50), Inches(11.4), Inches(1.7), "From records\nto reasoning", size=46, bold=True,
     color=INK, font=TITLE_FONT, spacing=0.95)
text(s, Inches(0.8), Inches(3.42), Inches(11.0), Inches(0.9),
     "A semantic and contextual layer that gives AI meaning, precedence and authority —\n"
     "proven on three insurance decisions, built to extend.",
     size=14, color=MUTED, spacing=1.3)
card(s, Inches(0.8), Inches(4.52), Inches(11.6), Inches(1.36), fill=CARD)
text(s, Inches(1.05), Inches(4.70), Inches(3.2), Inches(0.4), "3 decisions", size=19, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(1.05), Inches(5.12), Inches(3.2), Inches(0.4), "fleet renewal · reserving · pricing", size=11, color=MUTED)
text(s, Inches(4.35), Inches(4.70), Inches(3.2), Inches(0.4), "6 entities", size=19, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(4.35), Inches(5.12), Inches(3.2), Inches(0.4), "aligned to the OMG P&C model", size=11, color=MUTED)
text(s, Inches(7.65), Inches(4.70), Inches(3.4), Inches(0.4), "82 tests", size=19, bold=True, color=ACCENT, font=TITLE_FONT)
text(s, Inches(7.65), Inches(5.12), Inches(4.2), Inches(0.4), "running today, not slideware", size=11, color=MUTED)
text(s, Inches(0.8), Inches(6.55), Inches(11.6), Inches(0.3),
     "Visionet  |  Insurance Knowledge Framework  |  Client proposition  ·  v1.1  ·  Illustrative scenarios, not underwriting policy",
     size=10, color=MUTED)

# ==========================================================================
# 2 — the story
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The story", "AI does not fail on models. It fails on meaning.",
      "A customer journey crosses six systems. Each is authoritative for something different — and none can answer alone.", 2)

three_cards(s, [
    ("1", "FRAGMENTED", "Four truths, one customer",
     ["Policy admin: covered.",
      "Claims: money reserved.",
      "Billing: premium unpaid.",
      "Underwriting: risk declined."],
     "A person reconciles this by instinct. An agent cannot."),
    ("2", "MEANING", "One model, with time on it",
     ["One name and key per thing.",
      "Typed links, carrying dates.",
      "A truck that moves keeps one history."],
     "Meaning is encoded once, not re-derived in every report."),
    ("3", "DECISION", "Evidence, not just a number",
     ["Rules read the model, not a sheet.",
      "Every point shows its attribute.",
      "Every answer names who decides."],
     "Same input, same answer, every time."),
], y=Inches(2.0), h=Inches(3.3))

band(s, Inches(5.55), Inches(1.0), "The gap",
     "It is not data volume. It is meaning, precedence and authority — and today those live in people's heads, "
     "which is exactly what an agent cannot inherit.")
notes(s, "The failure mode is not the model; it is that four systems each tell a true, partial story.")

# ==========================================================================
# 3 — the use case
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Use case  ·  fleet renewal", "Context-aware risk assessment at renewal",
      "Three governed metrics + two rules + historical exposure relationships + lifecycle impact.", 3)

card(s, Inches(0.55), Inches(1.88), Inches(12.2), Inches(0.95))
text(s, Inches(0.78), Inches(1.99), Inches(2.4), Inches(0.24), "BUSINESS SCENARIO", size=9.5, bold=True, color=ACCENT)
text(s, Inches(0.78), Inches(2.25), Inches(2.5), Inches(0.5), "ABC Express renews P205\n40 vehicles transferred", size=10.5, color=INK, spacing=1.2)

steps = [
    ("2025 · BEFORE RESTRUCTURING", "100 vehicles"),
    ("2026 · TWO ENTITIES", "90 + 60 vehicles"),
    ("P205 · JAN 2027", "60-vehicle renewal"),
]
sx = Inches(3.35)
for head, value in steps:
    card(s, sx, Inches(1.96), Inches(2.85), Inches(0.68), fill=WHITE)
    text(s, sx + Inches(0.14), Inches(2.02), Inches(2.6), Inches(0.2), head, size=9, color=MUTED)
    text(s, sx + Inches(0.14), Inches(2.24), Inches(2.6), Inches(0.3), value, size=12, bold=True, color=INK)
    sx += Inches(3.02)

three_cards(s, [
    ("1", "ONTOLOGY", "Connects changing exposures",
     ["Group: 150 vehicles, 2 entities",
      "P205: 60 vehicles; 40 transferred",
      "V041 → P101, ₹5L prior claim"],
     "Time-valid policy ↔ vehicle links"),
    ("2", "CONTEXT & RULES", "Selects the applicable rules",
     ["R1: loss ratio ≥60% → refer",
      "R2: group >120 → group review",
      "V041 history = evidence only"],
     "Renewal Jan 2027 · high-risk fleet"),
    ("3", "SEMANTIC & LIFECYCLE", "Three metrics, one change",
     ["Loss ratio 60% (v2, incl. ALAE)",
      "Frequency 13.3 / 100 veh-years",
      "Severity ₹30k / claim"],
     "v1 → v2: 50% → 60%; trace impact"),
], y=Inches(3.0), h=Inches(2.45))

band(s, Inches(5.58), Inches(0.78), "Recommendation",
     "Refer P205 for senior review; group assessment required. The underwriter retains the final decision.")
text(s, Inches(0.55), Inches(6.55), Inches(11.6), Inches(0.3),
     "BUSINESS FUNCTIONS   Underwriting · Actuarial · Claims · Risk Management · BI / Analytics",
     size=9.5, bold=True, color=INK)

# ==========================================================================
# 4 — the layer
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The layer", "A runtime contract, not a glossary",
      "Five capabilities that machines and people both consume. The ontology defines meaning; context decides which meaning applies.", 4)

caps = [
    ("1", "CANONICAL\nENTITIES", "Customer · Policy ·\nProperty · Vehicle ·\nCoverage · Claim", "One name, one key, one owner."),
    ("2", "RELATION-\nSHIPS", "Covers · owns ·\narisesFrom · insuredBy", "Typed, directed — and dated."),
    ("3", "TAXO-\nNOMIES", "Loss causes · occupancy ·\ncoverage classes", "The controlled vocabulary."),
    ("4", "CONSTRAINTS\n& INFERENCE", "Validation · integrity ·\nhard stops", "What must be true; what is derived."),
    ("5", "CONTEXT\n& AUTHORITY", "Who asks · as at when ·\nread, recommend, commit", "Same data, different permitted answer."),
]
cx = Inches(0.55)
cw = Inches(2.3)
for num, head, mid, foot in caps:
    card(s, cx, Inches(1.95), cw, Inches(3.35))
    chip(s, cx + Inches(0.16), Inches(2.10), Inches(0.32), num)
    text(s, cx + Inches(0.56), Inches(2.14), cw - Inches(0.7), Inches(0.6), head, size=9.5, bold=True, color=INK, spacing=1.0)
    text(s, cx + Inches(0.16), Inches(2.90), cw - Inches(0.32), Inches(0.95), mid, size=11, color=ACCENT, spacing=1.15)
    text(s, cx + Inches(0.16), Inches(4.10), cw - Inches(0.32), Inches(0.9), foot, size=11, color=MUTED, spacing=1.15)
    cx += cw + Inches(0.12)

band(s, Inches(5.55), Inches(1.0), "Context is the part everyone skips",
     "Read · Recommend · Commit — stated per role and per agent. Time is part of the context: ‘which fleet covered "
     "this vehicle at renewal’ is unanswerable without a dated edge.")

# ==========================================================================
# 5 — standards landscape (new)
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Standards", "Standards give vocabulary, not volume",
      "Three families. We adopted the first, ignored the second, and stay ready for the third.", 5)

cols = [
    ("CONTENT MODELS", "what insurance data is made of",
     ["OMG P&C Data Model — used here", "ACORD — member licensed", "riskine ontology — Apache-2.0", "FIBO — legal entities, MIT"]),
    ("REPORTING TAXONOMIES", "what you must file",
     ["Solvency II XBRL (EIOPA)", "IFRS 17 taxonomy", "Statutory blanks (NAIC)", "—", ]),
    ("INTEROPERABILITY", "how you exchange it",
     ["OPIN — Open Insurance Brasil", "EU FiDA", "UK Open Finance", "ISO 20022"]),
]
x = Inches(0.55)
for head, sub, items in cols:
    card(s, x, Inches(1.95), Inches(3.9), Inches(2.95))
    text(s, x + Inches(0.24), Inches(2.10), Inches(3.4), Inches(0.3), head, size=10.5, bold=True, color=ACCENT)
    text(s, x + Inches(0.24), Inches(2.40), Inches(3.4), Inches(0.3), sub, size=11, color=MUTED)
    cy = Inches(2.85)
    for item in items:
        if item == "—":
            continue
        text(s, x + Inches(0.24), cy, Inches(3.45), Inches(0.4), "·  " + item, size=11, color=INK if item.endswith("used here") else MUTED, spacing=1.1)
        cy += Inches(0.45)
    x += Inches(4.13)

band(s, Inches(5.1), Inches(1.35), "What we did with them",
     "Aligned our six entities to the OMG P&C model — Customer → party, Policy → policy, Property → insurable_object, "
     "Coverage → coverage, Claim → claim — and verified the names against the model's own 256 tables. "
     "We use five of them, deliberately. ACORD and OPIN wait until a client needs conformance; "
     "reporting taxonomies wait until reporting is the driver.")

# ==========================================================================
# 6 — where it sits
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Architecture", "Where the layer sits",
      "Sources of record feed foundations; the semantic layer is the only place meaning lives; everything reads through it.", 6)

card(s, Inches(0.55), Inches(1.88), Inches(12.2), Inches(0.44), fill=WHITE, line=HAIR)
text(s, Inches(0.72), Inches(1.96), Inches(1.7), Inches(0.24), "CONTROL PLANE", size=9.5, bold=True, color=ACCENT)
text(s, Inches(2.35), Inches(1.96), Inches(10.2), Inches(0.24),
     "identity · catalog · lineage · policy as code · observability · cost", size=10.5, color=MUTED)

cols = [
    (Inches(0.55), Inches(2.35), "SOURCES", WHITE, HAIR, ["Policy admin", "Claims", "Billing", "UW desk", "Documents"]),
    (Inches(3.5), Inches(2.45), "DATA FOUNDATIONS", WHITE, HAIR,
     ["Bronze — raw", "Silver — conformed", "Gold — domain marts", "Quality · lineage"]),
    (Inches(6.5), Inches(3.1), "SEMANTIC LAYER", CARD, ACCENT,
     ["Canonical entities", "Relationships, with time", "Metric layer (versioned)", "Rules service", "Evidence store"]),
    (Inches(10.05), Inches(2.7), "EXPERIENCE", WHITE, HAIR, ["Workbench", "API / tools", "Agent runtime", "BI & reporting"]),
]
for x, w, head, fill, line, items in cols:
    card(s, x, Inches(2.5), w, Inches(3.0), fill=fill, line=line)
    text(s, x + Inches(0.18), Inches(2.64), w - Inches(0.36), Inches(0.24), head, size=9.5, bold=True,
         color=ACCENT if head == "SEMANTIC LAYER" else INK)
    cy = Inches(2.98)
    for item in items:
        text(s, x + Inches(0.18), cy, w - Inches(0.3), Inches(0.24), "·  " + item, size=11, color=MUTED)
        cy += Inches(0.44)

for x in (Inches(3.02), Inches(6.03), Inches(9.7)):
    chevron(s, x, Inches(3.85))

text(s, Inches(0.55), Inches(5.68), Inches(12.2), Inches(0.3),
     "RUNNING TODAY  ·  PRODUCTION SUBSTITUTES COMPONENTS, NOT THE MODEL", size=9.5, bold=True, color=INK)
text(s, Inches(0.55), Inches(5.98), Inches(12.2), Inches(0.9),
     "Today: CSV sources · in-memory graph · YAML ontology and metrics · Python rules service · FastAPI · Streamlit.\n"
     "Production: lakehouse (Delta) · Neo4j Aura · governed catalogue and metric layer · API management + identity · embedded in UW and claims screens.",
     size=10.5, color=MUTED, spacing=1.25)

# ==========================================================================
# 7 — POC vs production
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Components", "Prove the model, replace the plumbing",
      "Replace one component at a time. The ontology, the metric definitions and the evidence contract stay stable.", 7)

rows = [
    ['Ontology repo', 'YAML in Git', 'Governed catalog, releases', 'One definition, reviewable'],
    ['Graph store', 'In-memory traversal', 'Neo4j Aura or equivalent', 'Multi-hop at scale'],
    ['Lakehouse', 'Sample CSV book', 'Databricks / Fabric + Delta', 'History and lineage'],
    ['Rules', 'Python, config-driven', 'Rules service + decision log', 'Auditable, replayable'],
    ['Metric layer', 'YAML definitions', 'dbt / Unity metrics', 'Governed, reusable'],
    ['API & identity', 'FastAPI, local', 'API management + Entra ID', 'Access per role'],
    ['Experience', 'Streamlit workbench', 'Embedded in UW / claims', 'Adoption in workflow'],
    ['Documents', 'Not in the POC', 'Extraction + embeddings', 'Unstructured evidence'],
]
table(s, ['Capability', 'POC today', 'Production option', 'Why it matters'], rows,
      Inches(0.55), Inches(1.92), Inches(12.2), Inches(4.4), ratios=[1.9, 2.7, 3.1, 3.1])

text(s, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.3),
     "Already running: three decisions, 82 tests, an API, a workbench, and an assistant that answers from tools.",
     size=10.5, color=MUTED)

# ==========================================================================
# 8 — business outcomes
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Business outcomes", "Where the value lands",
      "Five value streams share one spine. Each KPI is a hypothesis with a baseline and an owner.", 8)

rows = [
    ['Underwriting renewal', 'Policy-only view becomes policy + group + transfer history', 'Referral pack time · precision'],
    ['Claims reserving', 'Adverse development decomposed, not asserted', 'Reserving cycle · audit findings'],
    ['Pricing', 'Indication from versioned assumptions, with sensitivity', 'Quote turnaround · rate adequacy'],
    ['Data onboarding', 'New source maps to canonical entities', 'Effort per new source'],
    ['Governance', 'One definition per metric, with impact trace', 'Metric disputes · restatements'],
]
table(s, ['Value stream', 'What changes', 'KPI to baseline'], rows,
      Inches(0.55), Inches(1.95), Inches(12.2), Inches(3.3), ratios=[2.2, 6.2, 3.2])

band(s, Inches(5.55), Inches(1.0), "The honest part",
     "We are not quoting percentages yet. Each target is a hypothesis: baseline, owner, measurement window — "
     "and replacing these words with your numbers is the pilot's first job.")

# ==========================================================================
# 9 — roadmap + ask
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Roadmap", "90 days to prove, three quarters to scale",
      "Start narrow, prove one decision, extend the same spine — the model does not change as scope grows.", 9)

phases = [
    ("0–90 DAYS", "Prove", ["One value stream, one owner", "Six entities, ruleset v1.0", "Workbench + explained API", "82 tests, baseline metrics"]),
    ("Q2", "Pilot", ["Add claims and billing sources", "Three domains, 10× data", "Governed ontology repository", "Metric layer + lineage"]),
    ("Q3–Q4", "Scale", ["ACORD-aligned extensions", "Agent tools with authority", "Policy engine + audit trail", "Unit economics"]),
]
x = Inches(0.55)
for period, name, items in phases:
    card(s, x, Inches(1.95), Inches(3.9), Inches(3.05))
    text(s, x + Inches(0.24), Inches(2.10), Inches(3.4), Inches(0.22), period, size=9.5, bold=True, color=ACCENT)
    text(s, x + Inches(0.24), Inches(2.36), Inches(3.4), Inches(0.4), name, size=18, bold=True, color=INK, font=TITLE_FONT)
    cy = Inches(2.88)
    for item in items:
        text(s, x + Inches(0.24), cy, Inches(3.45), Inches(0.5), "—  " + item, size=11, color=MUTED, spacing=1.05)
        cy += Inches(0.52)
    x += Inches(4.13)

text(s, Inches(0.55), Inches(5.25), Inches(12.2), Inches(0.24), "GATES", size=9.5, bold=True, color=ACCENT)
text(s, Inches(0.55), Inches(5.52), Inches(12.2), Inches(0.3),
     "G1 decision quality — does the answer match your underwriter?      G2 adoption — is it used in the workflow?      G3 economics — is unit cost falling?",
     size=10.5, color=MUTED)

band(s, Inches(6.02), Inches(0.85), "The ask",
     "One value stream, one accountable owner, three domain stewards — and 90 days against a measured baseline.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
