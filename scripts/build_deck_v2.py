"""Visual rebuild of the Enterprise Knowledge Framework deck — same words, more shape.

    python scripts/build_deck_v2.py

Every sentence from the source deck is preserved. What changes is the form:
paragraphs become cards, lists become chips and rows, tables become bands.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "files" / "Insurance_Knowledge_Framework_v2_visual.pptx"

CARD = RGBColor(0xF4, 0xF2, 0xFB)
ACCENT = RGBColor(0x5C, 0x10, 0xFF)
SOFT = RGBColor(0xEA, 0xE2, 0xFF)
BAND = RGBColor(0xE8, 0xF5, 0xF6)
INK = RGBColor(0x1E, 0x23, 0x40)
MUTED = RGBColor(0x4E, 0x55, 0x6B)
HAIR = RGBColor(0xDE, 0xDB, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0F, 0x6E, 0x6E)
GREY = RGBColor(0xEC, 0xEC, 0xF2)
GREEN = RGBColor(0x2E, 0x9E, 0x5B)
AMBER = RGBColor(0xC0, 0x77, 0x18)
RED = RGBColor(0xC0, 0x3A, 0x2B)

FOOT = "Visionet  |  Enterprise Knowledge & Semantic Context Framework  ·  Source-Agnostic Architecture with Insurance Domain Pack"
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


def text(s, x, y, w, h, value, size=10, bold=False, color=MUTED, align=PP_ALIGN.LEFT, spacing=1.1,
         font="Aptos", anchor=MSO_ANCHOR.TOP):
    box = s.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(value.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font


def card(s, x, y, w, h, fill=CARD, line=None, radius=0.05):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
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


def pill(s, x, y, w, h, value, fill=ACCENT, color=WHITE, size=9, bold=True):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    _strip(shp)
    shp.adjustments[0] = 0.25
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = value
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Aptos"


def icon(s, kind, x, y, d, fill=ACCENT):
    shp = s.shapes.add_shape(kind, x, y, d, d)
    _strip(shp)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    return shp


def frame(s, kicker, title, sub, page):
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    _strip(bg)
    bg.fill.solid()
    bg.fill.fore_color.rgb = WHITE
    bg.line.fill.background()
    s.shapes._spTree.remove(bg._element)
    s.shapes._spTree.insert(2, bg._element)

    text(s, Inches(0.55), Inches(0.30), Inches(11), Inches(0.26), kicker.upper(), size=9.5, bold=True, color=ACCENT)
    size = 24 if len(title) <= 56 else 21
    text(s, Inches(0.55), Inches(0.56), Inches(12.2), Inches(0.55), title, size=size, bold=True, color=INK,
         font="Aptos Display")
    text(s, Inches(0.55), Inches(1.10), Inches(12.2), Inches(0.4), sub, size=10.5, color=MUTED)
    text(s, Inches(0.55), Inches(7.14), Inches(11.6), Inches(0.22), FOOT, size=8, color=MUTED)
    pill(s, Inches(12.74), Inches(7.08), Inches(0.3), Inches(0.26), str(page), size=8.5)


def band(s, y, h, label, statement, size=9.5):
    card(s, Inches(0.55), y, Inches(12.2), h, fill=BAND)
    text(s, Inches(0.75), y + Inches(0.10), Inches(11.8), Inches(0.22), label.upper(), size=8, bold=True, color=TEAL)
    text(s, Inches(0.75), y + Inches(0.32), Inches(11.8), h - Inches(0.38), statement, size=size, color=INK, spacing=1.15)


def bullets(s, x, y, w, items, size=9.5, gap=0.30, color=MUTED, dot=True):
    cy = y
    for item in items:
        text(s, x, cy, w, Inches(gap + 0.1), ("•  " if dot else "") + item, size=size, color=color, spacing=1.12)
        cy += Inches(gap)


# ==========================================================================
# 1 — title
# ==========================================================================
s = prs.slides.add_slide(BLANK)
card(s, Inches(0), Inches(0), W, Inches(0.10), fill=ACCENT, radius=0)
text(s, Inches(0.8), Inches(0.75), Inches(11), Inches(0.28), "ENTERPRISE KNOWLEDGE FRAMEWORK  |  PROPOSITION",
     size=10.5, bold=True, color=ACCENT)
text(s, Inches(0.8), Inches(1.05), Inches(8.0), Inches(1.05), "From Records\nto Reasoning", size=38, bold=True,
     color=INK, font="Aptos Display", spacing=0.95)
text(s, Inches(0.8), Inches(2.95), Inches(7.0), Inches(1.2),
     "A source-agnostic semantic and contextual engine—pre-configured with an Insurance Knowledge Pack—"
     "that gives AI meaning, precedence, and auditable authority.", size=12, color=MUTED, spacing=1.35)

# right: four systems -> one model
fx = Inches(9.35)
for i, name in enumerate(["Policy Admin", "Claims", "Billing", "UW Desk"]):
    card(s, fx, Inches(1.10 + i * 0.50), Inches(1.4), Inches(0.36), fill=GREY)
    text(s, fx + Inches(0.10), Inches(1.16 + i * 0.50), Inches(1.25), Inches(0.22), name, size=8, color=MUTED)
icons = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(10.85), Inches(1.95), Inches(0.34), Inches(0.26))
_strip(icons)
icons.fill.solid()
icons.fill.fore_color.rgb = ACCENT
cx, cy = Inches(12.05), Inches(2.08)
pts = [(-0.40, -0.38), (0.40, -0.38), (-0.40, 0.38), (0.40, 0.38)]
for dx, dy in pts:
    conn = s.shapes.add_connector(1, cx, cy, cx + Inches(dx), cy + Inches(dy))
    conn.line.color.rgb = RGBColor(0xC9, 0xB8, 0xFF)
    conn.line.width = Pt(1.25)
for dx, dy in pts:
    dot = icon(s, MSO_SHAPE.OVAL, cx + Inches(dx) - Inches(0.08), cy + Inches(dy) - Inches(0.08), Inches(0.16), WHITE)
    dot.line.color.rgb = ACCENT
    dot.line.width = Pt(1.25)
icon(s, MSO_SHAPE.OVAL, cx - Inches(0.15), cy - Inches(0.15), Inches(0.30), ACCENT)

pillars = [
    ("Source-Agnostic Core", "Swap core systems or industries without rebuilding rules or agents", MSO_SHAPE.OVAL),
    ("Insurance Pack Ready", "6 canonical entities · OMG P&C aligned · 88 automated validation tests", MSO_SHAPE.DIAMOND),
    ("Deterministic + Auditable", "AI explains decisions; rules & metrics compute with immutable traces", MSO_SHAPE.HEXAGON),
]
x = Inches(0.8)
for head, body, kind in pillars:
    card(s, x, Inches(3.95), Inches(3.7), Inches(1.55))
    icon(s, kind, x + Inches(0.22), Inches(4.15), Inches(0.32))
    text(s, x + Inches(0.66), Inches(4.15), Inches(2.9), Inches(0.26), head, size=11, bold=True, color=INK)
    text(s, x + Inches(0.22), Inches(4.60), Inches(3.3), Inches(0.8), body, size=10, color=MUTED, spacing=1.2)
    x += Inches(3.9)

text(s, Inches(0.8), Inches(6.05), Inches(11.8), Inches(0.6),
     "Visionet  |  Enterprise Knowledge & Semantic Context Framework  ·  Source-Agnostic Architecture with Insurance Domain Pack",
     size=9, color=MUTED)

# ==========================================================================
# 2 — story
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The story  ·  business & data reality", "AI does not fail on models. It fails on meaning.",
      "One customer, four systems, four true statements that don't add up—creating leakage, delay, and audit risk.", 2)

card(s, Inches(0.55), Inches(1.55), Inches(5.95), Inches(4.35), fill=WHITE, line=HAIR)
text(s, Inches(0.75), Inches(1.68), Inches(5.5), Inches(0.24), "TODAY  ·  FOUR SILOED SYSTEMS (CONFLICTING TRUTHS)", size=8.5, bold=True, color=ACCENT)
systems = [("Policy Admin", "COVERED", GREEN, "active endorsement pending"),
           ("Claims System", "RESERVED", AMBER, "open ₹5L loss reserve"),
           ("Billing Ledger", "UNPAID", RED, "grace-period installment"),
           ("Underwriting Desk", "DECLINED", RED, "prior group referral")]
cy = Inches(2.00)
for name, status, colour, note in systems:
    card(s, Inches(0.75), cy, Inches(5.55), Inches(0.52), fill=CARD)
    text(s, Inches(0.90), cy + Inches(0.06), Inches(1.55), Inches(0.2), name, size=9, bold=True, color=INK)
    text(s, Inches(0.90), cy + Inches(0.26), Inches(3.1), Inches(0.2), note, size=8, color=MUTED)
    pill(s, Inches(4.55), cy + Inches(0.12), Inches(1.55), Inches(0.28), status, fill=WHITE, color=colour, size=8.5)
    s.shapes[-1].line.color.rgb = colour
    s.shapes[-1].line.width = Pt(1)
    cy += Inches(0.60)

text(s, Inches(0.75), Inches(4.52), Inches(5.4), Inches(0.2), "BUSINESS IMPACT OF FRAGMENTATION", size=8, bold=True, color=ACCENT)
bullets(s, Inches(0.75), Inches(4.76), Inches(5.55), [
    "Premium Leakage: Transferred risks priced without full loss history.",
    "Swivel-Chair Delay: Underwriters spend hours reconciling screens.",
    "Regulatory Exposure: Inability to reproduce why a decision was made.",
], size=9, gap=0.34)

card(s, Inches(6.80), Inches(1.55), Inches(5.95), Inches(4.35), fill=CARD)
text(s, Inches(7.00), Inches(1.68), Inches(5.5), Inches(0.24), "WITH THE LAYER  ·  ONE CANONICAL MODEL & TIMELINE", size=8.5, bold=True, color=ACCENT)
bullets(s, Inches(7.00), Inches(2.00), Inches(5.55), [
    "Resolved Identity: One customer, one key, one bi-temporal timeline.",
    "Canonical Entities: Customer · Policy · Property/Vehicle · Coverage · Claim.",
    "Precedence & Authority: Explicit rules resolve conflicts across sources.",
    "Source Independence: If Policy Admin or Claims changes, the model holds.",
], size=9, gap=0.36)
text(s, Inches(7.00), Inches(3.62), Inches(5.4), Inches(0.2), "OUTCOME FOR PEOPLE & AI AGENTS", size=8, bold=True, color=ACCENT)
bullets(s, Inches(7.00), Inches(3.86), Inches(5.55), [
    "Ask the question once; get one reproducible, governed answer.",
    "Every figure carries its definition version, timestamp, and lineage.",
    "Ready for underwriting, claims, finance—or any non-insurance domain.",
], size=9, gap=0.36)

band(s, Inches(6.02), Inches(0.98), "The core gap",
     "It is not data volume or LLM capability. It is meaning, precedence, and authority. Today those live in senior "
     "underwriters' heads—which an AI agent cannot inherit unless encoded into a semantic and contextual layer.")

# ==========================================================================
# 3 — use case
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Use case  ·  fleet renewal", "Context-aware risk assessment at renewal",
      "A truck moved between policies. The individual policy looks safer; the group book doesn't.", 3)

steps = [("2025  ·  BASELINE", "100 vehicles insured on Policy P205 under single fleet schedule."),
         ("2026  ·  MID-TERM SPLIT", "Split into 90 + 60 vehicles across 2 entities (150 group total). Truck V041 (₹5L claim) moves."),
         ("JAN 2027  ·  RENEWAL", "P205 renews with 60 vehicles. Standard SQL sees a cleaner policy; graph sees full history.")]
x = Inches(0.55)
for i, (head, body) in enumerate(steps):
    fill = SOFT if i == 0 else (RGBColor(0xC9, 0xB8, 0xFF) if i == 1 else ACCENT)
    colour = INK if i < 2 else WHITE
    card(s, x, Inches(1.55), Inches(3.95), Inches(1.25), fill=fill)
    text(s, x + Inches(0.2), Inches(1.66), Inches(3.5), Inches(0.22), head, size=8.5, bold=True, color=colour)
    text(s, x + Inches(0.2), Inches(1.90), Inches(3.55), Inches(0.85), body, size=9, color=colour, spacing=1.15)
    x += Inches(4.13)

cols = [
    ("1. ONTOLOGY & GRAPH", MSO_SHAPE.OVAL, ["150 vehicles across 2 entities.", "40 transferred; V041 tracked.",
                                             "V041 carried a ₹5L claim.", "Time-valid (bi-temporal) links preserve prior cover history."]),
    ("2. METRICS & LIFECYCLE", MSO_SHAPE.DIAMOND, ["Loss ratio: 60% (v2, +ALAE).", "Frequency: 13.3 / 100 veh-yr.",
                                                   "Severity: ₹30k / claim.", "Versioned definitions: v1 → v2 shifts 2 of 2 cohorts."]),
    ("3. CONTEXT & RULES", MSO_SHAPE.RECTANGLE, ["R1: Loss ratio ≥ 60% → Refer.", "R2: Group > 120 → Group review.",
                                                 "V041 prior loss = evidence only.", "Deterministic rules read the model; LLM never guesses math."]),
    ("4. RECOMMENDATION", MSO_SHAPE.HEXAGON, ["Refer P205 for senior review.", "Mandatory group assessment.",
                                              "Full evidence trace attached.", "Human underwriter retains final commit authority."]),
]
x = Inches(0.55)
for head, kind, items in cols:
    card(s, x, Inches(2.95), Inches(2.95), Inches(2.55))
    icon(s, kind, x + Inches(0.18), Inches(3.10), Inches(0.26))
    text(s, x + Inches(0.52), Inches(3.12), Inches(2.3), Inches(0.22), head, size=8.5, bold=True, color=INK)
    bullets(s, x + Inches(0.18), Inches(3.52), Inches(2.62), items, size=9, gap=0.44)
    x += Inches(3.09)

band(s, Inches(5.70), Inches(0.95), "Why this matters",
     "If the insurer replaces its Policy Admin system tomorrow, the canonical ontology, temporal cover edges, and referral "
     "rules remain untouched—only the source mapping adapter changes.")

# ==========================================================================
# 4 — five capabilities
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "The layer  ·  core capabilities", "Five capabilities, one semantic contract",
      "Machines and people consume the exact same definitions—making every answer deterministic and reproducible.", 4)

caps = [
    ("1. ENTITIES", MSO_SHAPE.OVAL, "Canonical nouns decoupled from source schemas:",
     ["Insurance: Customer, Policy, Property, Vehicle, Coverage, Claim.", "Cross-Industry: Party, Agreement, Asset, Event, Obligation."]),
    ("2. RELATIONSHIPS", MSO_SHAPE.DIAMOND, "Typed, directional, and bi-temporal edges:",
     ["Covers, owns, arisesFrom, belongsToGroup.", "Valid-from / valid-to dates answer 'as-at' historical questions."]),
    ("3. TAXONOMIES", MSO_SHAPE.RECTANGLE, "Controlled enterprise vocabularies & hierarchies:",
     ["Loss causes, occupancy codes, coverage classes.", "Harmonises conflicting code sets across acquired books."]),
    ("4. CONSTRAINTS", MSO_SHAPE.ISOSCELES_TRIANGLE, "Structural & business integrity guardrails:",
     ["Mandatory keys, referential integrity, hard stops.", "Blocks incomplete or contradictory records before reasoning."]),
    ("5. CONTEXT & AUTHORITY", MSO_SHAPE.HEXAGON, "Dynamic execution envelope per request:",
     ["Who is asking (human role vs. AI agent).", "As-at date + metric version.", "Permission tier: Read · Recommend · Commit."]),
]
x = Inches(0.55)
for head, kind, lead, items in caps:
    card(s, x, Inches(1.60), Inches(2.32), Inches(4.35))
    icon(s, kind, x + Inches(0.90), Inches(1.82), Inches(0.5))
    text(s, x + Inches(0.12), Inches(2.48), Inches(2.08), Inches(0.22), head, size=8.5, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.16), Inches(2.78), Inches(2.0), Inches(0.8), lead, size=9.5, color=INK, align=PP_ALIGN.CENTER, spacing=1.15)
    bullets(s, x + Inches(0.16), Inches(3.70), Inches(2.05), items, size=8.8, gap=0.6, dot=False)
    x += Inches(2.42)

band(s, Inches(6.05), Inches(1.0), "Context is the part everyone skips",
     "Separating Read · Recommend · Commit per role and per agent prevents unauthorized AI actions. Time is context too: "
     "'Which fleet covered this vehicle at renewal?' is unanswerable without dated edges.")

# ==========================================================================
# 5 — standards
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Standards & portability", "Standards give vocabulary, not volume—and keep the core portable",
      "Plug in industry content models without rewriting the underlying semantic, metric, or rules engine.", 5)

groups = [
    ("CONTENT MODELS (PLUGGABLE)", [
        ("OMG P&C (used here)", "Open, canonical P&C entity model."),
        ("ACORD", "Member-aligned insurance messaging & data standard."),
        ("riskine", "Open-source (Apache-2.0) insurance ontology."),
        ("FIBO", "Financial Industry Business Ontology for banking/legal entities."),
        ("Custom / Other", "Supply chain, healthcare (FHIR), or telecom schemas."),
    ], True),
    ("REGULATORY & REPORTING", [
        ("Solvency II XBRL", "European prudential capital & risk reporting."),
        ("IFRS 17 Taxonomy", "Insurance contract measurement & CSM tracking."),
        ("NAIC Statutory Blanks", "US regulatory financial schedules."),
        ("IRDAI / Local Filings", "Auditable lineage from board pack to source."),
        ("EU AI Act / Model Risk", "Versioned decision & rule provenance."),
    ], False),
    ("INTEROPERABILITY & APIs", [
        ("OPIN", "Open Insurance Brasil ecosystem."),
        ("EU FiDA & UK Open Finance", "Consent-driven financial data sharing."),
        ("ISO 20022", "Standardized payment and settlement messaging."),
        ("MCP (Model Context Protocol)", "Universal tool contract for AI agents."),
        ("OpenLineage / REST / GraphQL", "Open integration surface."),
    ], False),
]
x = Inches(0.55)
for head, items, chosen in groups:
    card(s, x, Inches(1.55), Inches(3.95), Inches(3.95), fill=CARD if chosen else WHITE, line=None if chosen else HAIR)
    text(s, x + Inches(0.2), Inches(1.68), Inches(3.5), Inches(0.22), head, size=8.5, bold=True, color=ACCENT)
    cy = Inches(2.00)
    for name, desc in items:
        card(s, x + Inches(0.18), cy, Inches(3.6), Inches(0.62), fill=WHITE if not chosen else SOFT)
        text(s, x + Inches(0.30), cy + Inches(0.06), Inches(3.3), Inches(0.2), name, size=8.8, bold=True, color=INK)
        text(s, x + Inches(0.30), cy + Inches(0.26), Inches(3.35), Inches(0.32), desc, size=7.8, color=MUTED, spacing=1.05)
        cy += Inches(0.68)
    x += Inches(4.13)

band(s, Inches(5.68), Inches(1.25), "What we did & why it scales across sources",
     "We mapped Customer → party, Policy → policy, Property → insurable_object, Coverage → coverage, Claim → claim against "
     "OMG P&C's 256 tables—using five deliberately. Because source systems map into canonical adapters, replacing a legacy "
     "Policy Admin platform (or swapping the OMG P&C pack for FIBO in Banking) leaves the graph engine, rules service, and AI agents intact.")

# ==========================================================================
# 6 — architecture
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Architecture  ·  composable & source-agnostic", "Overall architecture: decoupled kernel, pluggable sources & packs",
      "Everything reads through the middle semantic column. Nothing reads system-to-system.", 6)

card(s, Inches(0.55), Inches(1.50), Inches(12.2), Inches(0.36), fill=WHITE, line=HAIR)
text(s, Inches(0.72), Inches(1.57), Inches(11.9), Inches(0.22),
     "GOVERNANCE & CONTROL PLANE:   Identity & Entra ID   ·   Metadata Catalog   ·   End-to-End Lineage   ·   Policy-as-Code   ·   Observability",
     size=9, bold=True, color=ACCENT)

blocks = [
    (Inches(0.55), Inches(2.55), "1. SOURCES (ANY SYSTEM)", WHITE, HAIR,
     ["Insurance Systems:", "Policy Admin (Guidewire, Duck Creek)", "Claims & Billing Ledgers", "UW Workbench & Bordereaux",
      "", "Or Any Other Domain:", "ERP / CRM (SAP, Salesforce)", "Core Banking / Telemetry / Docs", "Hot (CDC/Kafka) & Batch Feeds"]),
    (Inches(3.55), Inches(2.6), "2. CANONICAL ADAPTERS", WHITE, HAIR,
     ["Decoupling & Ingestion:", "Bronze — Raw immutable landing", "Silver — Conformed & DQ-checked", "Gold — Curated domain marts",
      "", "Source-Change Shield:", "Entity Resolution (Cross-Walk IDs)", "Declarative Source-to-Ontology Map", "Swap sources without touching rules"]),
    (Inches(6.55), Inches(2.9), "3. SEMANTIC & CONTEXT KERNEL", SOFT, ACCENT,
     ["Source-Agnostic Core Engine:", "Ontology & Bi-Temporal Graph", "Versioned Metric Compiler", "Deterministic Rules Service",
      "Context & Authority Gate (R/R/C)", "Immutable Evidence Store", "", "Pluggable Domain Pack:", "Insurance (OMG P&C) / Banking / etc."]),
    (Inches(9.90), Inches(2.85), "4. EXPERIENCE & AGENTS", WHITE, HAIR,
     ["Governed Consumption:", "Underwriter / Claims Workbench", "MCP Server & REST/GraphQL APIs", "AI Agent Runtime (Copilot / Bedrock)",
      "Executive BI & Regulatory Packs", "", "Zero Lock-In:", "Any LLM or UI consumes the exact same governed tool surface"]),
]
for x, w, head, fill, line, items in blocks:
    card(s, x, Inches(2.0), w, Inches(3.65), fill=fill, line=line)
    text(s, x + Inches(0.16), Inches(2.12), w - Inches(0.3), Inches(0.22), head, size=8.5, bold=True,
         color=ACCENT if head.startswith("3") else INK)
    cy = Inches(2.42)
    for item in items:
        if not item:
            cy += Inches(0.12)
            continue
        bold = item.endswith(":")
        text(s, x + Inches(0.16), cy, w - Inches(0.3), Inches(0.3), ("·  " if not bold else "") + item,
             size=8.2, bold=bold, color=ACCENT if bold else MUTED, spacing=1.05)
        cy += Inches(0.33)

band(s, Inches(5.92), Inches(0.95), "POC → production continuity",
     "POC runs on CSVs · In-memory graph · YAML ontology · Python rules · FastAPI · Streamlit. Production swaps infrastructure "
     "(Delta Lakehouse · Neo4j Aura · Governed Catalog · APIM) without changing the ontology or rules.")

# ==========================================================================
# 7 — inside the layer
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Inside the layer  ·  AI guardrails", "What sits inside—and where the AI is strictly allowed to stand",
      "Definitions on the left, evidence on the right. The graph holds facts; the trace holds reasoning.", 7)

card(s, Inches(0.55), Inches(1.55), Inches(2.5), Inches(4.2), fill=WHITE, line=HAIR)
text(s, Inches(0.72), Inches(1.68), Inches(2.2), Inches(0.22), "INGEST & MAP", size=8.5, bold=True, color=ACCENT)
bullets(s, Inches(0.72), Inches(2.00), Inches(2.2), [
    "Policy, Claims, Billing, UW & Unstructured Docs.",
    "Schema validation & entity resolution.",
    "Hot path (events) + Cold path (batch).",
    "Isolates downstream logic from source schema drift.",
], size=8.5, gap=0.78)

card(s, Inches(3.20), Inches(1.55), Inches(5.0), Inches(4.2), fill=CARD)
text(s, Inches(3.38), Inches(1.68), Inches(4.6), Inches(0.22), "INSIDE THE SEMANTIC & CONTEXT LAYER", size=8.5, bold=True, color=ACCENT)
inner = [
    ("Ontology Repo", "Canonical entities (party, policy, cover, claim) & taxonomies."),
    ("Bi-Temporal Graph Store", "Dated cover edges, fleet transfers & claim links."),
    ("Versioned Metric Layer", "Loss ratio, frequency, severity (v1, v2 +ALAE)."),
    ("Deterministic Rules Service", "Referral thresholds, hard stops & precedence."),
    ("Context Gate", "As-at date · Definition version · Caller identity · R/R/C rights."),
    ("Evidence Store", "Every decision logged with exact inputs, versions & trace."),
    ("MCP / Tool Surface", "Standardised assess · history · impact tools."),
]
cy = Inches(2.00)
for name, desc in inner:
    card(s, Inches(3.36), cy, Inches(4.66), Inches(0.48), fill=WHITE)
    text(s, Inches(3.50), cy + Inches(0.05), Inches(4.4), Inches(0.2), name, size=8.5, bold=True, color=INK)
    text(s, Inches(3.50), cy + Inches(0.24), Inches(4.4), Inches(0.2), desc, size=7.8, color=MUTED)
    cy += Inches(0.52)

card(s, Inches(8.45), Inches(1.55), Inches(4.3), Inches(4.2), fill=WHITE, line=HAIR)
text(s, Inches(8.63), Inches(1.68), Inches(4.0), Inches(0.22), "CONSUMERS & AI BOUNDARY", size=8.5, bold=True, color=ACCENT)
text(s, Inches(8.63), Inches(2.00), Inches(4.0), Inches(0.2), "Deterministic Consumers:", size=8.5, bold=True, color=INK)
bullets(s, Inches(8.63), Inches(2.24), Inches(3.95), ["UW Workbench, APIs & BI dashboards."], size=8.5, gap=0.3)
card(s, Inches(8.63), Inches(2.70), Inches(3.95), Inches(1.05), fill=ACCENT)
text(s, Inches(8.78), Inches(2.78), Inches(3.7), Inches(0.2), "AI / Agent Runtime (Outside Layer)", size=8.5, bold=True, color=WHITE)
text(s, Inches(8.78), Inches(3.00), Inches(3.7), Inches(0.7),
     "Drafts FNOL summaries & renewal notes · Explains referrals in plain language", size=7.8, color=WHITE, spacing=1.1)
bullets(s, Inches(8.63), Inches(3.90), Inches(3.95), [
    "NEVER computes metrics or overrides rules.",
    "Every number comes from governed tools.",
], size=8.5, gap=0.32)

band(s, Inches(5.92), Inches(0.95), "The architectural boundary",
     "LLMs are probabilistic; insurance pricing, coverage, and referrals must be deterministic. Keeping the agent outside the "
     "computation boundary eliminates hallucinated math while giving AI full narrative context.")

# ==========================================================================
# 8 — components
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Technical components  ·  swappable stack", "Prove the model in weeks; swap components without rework",
      "Six modular components swapped one at a time. The ontology, rules, and evidence contract stay put.", 8)

rows = [
    ("Ontology & Metric Repo", "Declarative YAML in Git", "Governed Enterprise Catalog", "Canonical entities, definitions & versions"),
    ("Graph Store", "In-memory property graph", "Neo4j Aura / Enterprise Graph", "Bi-temporal edge semantics & traversals"),
    ("Lakehouse & Adapters", "Sample CSVs + Python loaders", "Delta on Fabric / Databricks + CDC", "Source-to-canonical mapping contracts"),
    ("Rules & Evidence Engine", "Python rules service + JSON log", "Containerised Rules + Immutable Audit DB", "Deterministic thresholds & trace schema"),
    ("API, MCP & Identity", "FastAPI (local) + mock roles", "APIM + Entra ID + MCP Gateway", "Read · Recommend · Commit authority gates"),
    ("User & Agent Experience", "Streamlit UW prototype", "Embedded UW Desk + Enterprise Agents", "Explainable decision cards & citations"),
]
text(s, Inches(0.55), Inches(1.52), Inches(2.4), Inches(0.2), "COMPONENT", size=8, bold=True, color=MUTED)
text(s, Inches(3.05), Inches(1.52), Inches(3.0), Inches(0.2), "POC TODAY (FAST PROOF)", size=8, bold=True, color=MUTED)
text(s, Inches(6.35), Inches(1.52), Inches(3.2), Inches(0.2), "PRODUCTION TARGET", size=8, bold=True, color=ACCENT)
text(s, Inches(9.85), Inches(1.52), Inches(2.9), Inches(0.2), "WHAT STAYS CONSTANT", size=8, bold=True, color=TEAL)

cy = Inches(1.80)
for i, (name, poc, prod, stays) in enumerate(rows):
    card(s, Inches(0.55), cy, Inches(12.2), Inches(0.62), fill=CARD if i % 2 == 0 else WHITE, line=None if i % 2 == 0 else HAIR)
    text(s, Inches(0.72), cy + Inches(0.10), Inches(2.3), Inches(0.4), name, size=8.8, bold=True, color=INK, spacing=1.05)
    text(s, Inches(3.05), cy + Inches(0.10), Inches(3.0), Inches(0.4), poc, size=8.5, color=MUTED, spacing=1.05)
    s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(6.05), cy + Inches(0.20), Inches(0.24), Inches(0.2))
    arrow = s.shapes[-1]
    _strip(arrow)
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = ACCENT
    text(s, Inches(6.42), cy + Inches(0.10), Inches(3.2), Inches(0.4), prod, size=8.5, bold=True, color=ACCENT, spacing=1.05)
    text(s, Inches(9.85), cy + Inches(0.10), Inches(2.8), Inches(0.4), stays, size=8.5, color=TEAL, spacing=1.05)
    cy += Inches(0.68)

band(s, Inches(6.02), Inches(0.9), "Zero re-engineering at scale",
     "Same six entities. Same deterministic rules. Same evidence contract. Moving from POC to enterprise production requires "
     "a new cluster and governed connectors—never a new domain model.")

# ==========================================================================
# 9 — outcomes
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Business outcomes  ·  insurance value moments", "Where the value lands across the insurance value chain",
      "Five high-leverage decision moments—and how the semantic layer transforms speed, accuracy, and auditability.", 9)

outs = [
    ("1. RENEWAL", MSO_SHAPE.OVAL, "Policy, group & vehicle transfer history on one screen.",
     ["Pack built in minutes, not days.", "Catches hidden cross-policy losses."]),
    ("2. FNOL TRIAGE", MSO_SHAPE.DIAMOND, "Coverage, prior losses & gaps checked at first notification.",
     ["Instant triage, zero re-keying.", "Flags fraud/coverage anomalies early."]),
    ("3. RESERVING", MSO_SHAPE.RECTANGLE, "Adverse loss development broken into root drivers.",
     ["E.g., ₹20 Cr → ₹23 Cr explained.", "Links claim drift to policy/cohort shifts."]),
    ("4. PRICING", MSO_SHAPE.ISOSCELES_TRIANGLE, "Technical indication from versioned assumptions & sensitivity.",
     ["E.g., ₹10L → ₹12.79L indicated.", "Full version lineage for actuaries."]),
    ("5. ONBOARDING", MSO_SHAPE.HEXAGON, "New MGA scheme or bordereaux mapped to canonical entities.",
     ["16 columns mapped once.", "Reusable across all downstream BI/AI."]),
]
x = Inches(0.55)
for head, kind, lead, items in outs:
    card(s, x, Inches(1.60), Inches(2.32), Inches(3.95))
    icon(s, kind, x + Inches(0.90), Inches(1.82), Inches(0.5))
    text(s, x + Inches(0.12), Inches(2.48), Inches(2.08), Inches(0.22), head, size=8.5, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.16), Inches(2.78), Inches(2.0), Inches(0.9), lead, size=9, color=INK, align=PP_ALIGN.CENTER, spacing=1.15)
    bullets(s, x + Inches(0.16), Inches(3.95), Inches(2.05), items, size=8.5, gap=0.55, dot=False)
    x += Inches(2.42)

band(s, Inches(5.75), Inches(1.15), "The honest part (measured value)",
     "No generic inflated ROI percentages here. Each outcome requires your historical baseline, an accountable business owner, "
     "and a 90-day measurement window on a live book of business—and the exact same pattern applies to credit underwriting, "
     "supply chain risk, or healthcare claims.")

# ==========================================================================
# 10 — roadmap
# ==========================================================================
s = prs.slides.add_slide(BLANK)
frame(s, "Roadmap & execution  ·  90 days to prove", "90 days to prove, three quarters to scale",
      "Start with one high-value stream. The semantic spine stays constant as domains and sources expand.", 10)

phases = [
    ("DAYS 0–90: PROVE (SHADOW MODE)", "Prove", ACCENT,
     ["Scope: 1 value stream (e.g., Fleet Renewal).", "Model: 6 canonical entities + 88 automated tests.",
      "Execution: Shadow-mode scoring against 100 historical renewals.", "Gate: Reproducible decision trace & underwriter sign-off."]),
    ("Q2: PILOT (PRODUCTION WORKFLOW)", "Pilot", RGBColor(0x8B, 0x5C, 0xFF),
     ["Scope: Expand to 3 domains (Policy, Claims, Billing).", "Scale: 10× data volume in governed Lakehouse + Graph.",
      "Governance: Full Entra ID role gates (Read / Recommend / Commit).", "Gate: Live adoption in underwriter workbench."]),
    ("Q3–Q4: SCALE (ENTERPRISE SPINE)", "Scale", RGBColor(0xC0, 0xA8, 0xFF),
     ["Scope: ACORD / multi-line alignment + bordereaux onboarding.", "AI Autonomy: Controlled agent authority via MCP tools.",
      "Portability: Onboard new core systems or adjacent business units.", "Gate: Verified unit economics & regulatory audit readiness."]),
]
x = Inches(0.55)
for head, name, colour, items in phases:
    card(s, x, Inches(1.55), Inches(3.95), Inches(3.75), fill=WHITE, line=HAIR)
    top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, Inches(1.55), Inches(3.95), Inches(0.09))
    _strip(top)
    top.fill.solid()
    top.fill.fore_color.rgb = colour
    text(s, x + Inches(0.22), Inches(1.74), Inches(3.5), Inches(0.22), head, size=8, bold=True, color=colour)
    text(s, x + Inches(0.22), Inches(1.98), Inches(3.4), Inches(0.35), name, size=16, bold=True, color=INK, font="Aptos Display")
    bullets(s, x + Inches(0.22), Inches(2.45), Inches(3.5), items, size=8.5, gap=0.62)
    x += Inches(4.13)

band(s, Inches(5.55), Inches(1.25), "The ask to get started",
     "1 accountable business owner  ·  1 priority value stream  ·  3 domain stewards (Policy, Claims, Actuarial/UW)  ·  "
     "90 days to benchmark decision quality, cycle time, and auditability against your measured baseline.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
