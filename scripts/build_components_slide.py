"""One slide: the six components of the semantic layer, POC vs production.

    python scripts/build_components_slide.py

Standalone deck so it can be dropped in as an appendix slide.
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
OUT = ROOT.parent / "files" / "Semantic_Layer_Components.pptx"

CARD = RGBColor(0xF4, 0xF2, 0xFB)
ACCENT = RGBColor(0x5C, 0x10, 0xFF)
BAND = RGBColor(0xE8, 0xF5, 0xF6)
INK = RGBColor(0x1E, 0x23, 0x40)
MUTED = RGBColor(0x4E, 0x55, 0x6B)
HAIR = RGBColor(0xDE, 0xDB, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0F, 0x6E, 0x6E)

W, H = Inches(13.333), Inches(7.5)
prs = Presentation()
prs.slide_width = W
prs.slide_height = H
slide = prs.slides.add_slide(prs.slide_layouts[6])


def _strip(shp):
    sp = shp._element
    style = sp.find(qn("p:style"))
    if style is not None:
        sp.remove(style)
    shp.shadow.inherit = False


def text(x, y, w, h, value, size=11, bold=False, color=MUTED, font="Aptos", align=PP_ALIGN.LEFT, spacing=1.0):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
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


def card(x, y, w, h, fill=CARD, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    _strip(shp)
    shp.adjustments[0] = 0.05
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


bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
_strip(bg)
bg.fill.solid()
bg.fill.fore_color.rgb = WHITE
bg.line.fill.background()
slide.shapes._spTree.remove(bg._element)
slide.shapes._spTree.insert(2, bg._element)

text(Inches(0.55), Inches(0.40), Inches(11), Inches(0.28), "THE LAYER  |  COMPONENTS", size=10.5, bold=True, color=ACCENT)
text(Inches(0.55), Inches(0.70), Inches(12.1), Inches(0.6), "Six components — and what each becomes in production",
     size=26, bold=True, color=INK, font="Aptos Display")
text(Inches(0.55), Inches(1.28), Inches(12.2), Inches(0.4),
     "One boundary per rate of change and owner — not one per technology.", size=11.5, color=MUTED)

rows = [
    ("Ontology repo", "what exists, and what the names mean", "ontology/*.yaml in Git",
     "governed catalog, versioned releases", "rarely, by review"),
    ("Graph store", "what is true now — and when", "Python dicts + traversal",
     "Neo4j Aura (in production)", "every load"),
    ("Metric layer", "how do we measure it", "fleet_metrics.yaml, pricing_inputs.yaml",
     "dbt / Unity metric views", "quarterly, actuarial"),
    ("Rules service", "what do we do about it", "rules.py + the rules blocks",
     "rules engine + decision log", "per UW policy"),
    ("Evidence store", "why did we decide that", "assessment object + tool trace (not persisted)",
     "append-only decision table + lineage", "append-only"),
    ("Tool surface", "who may ask, and how", "FastAPI + assistant Toolbox",
     "API gateway + tool server, Entra ID", "per consumer"),
]

headers = ["Component", "The question it answers", "POC today", "Production equivalent", "Changes when"]
col_w = [Inches(2.35), Inches(3.15), Inches(3.0), Inches(3.0), Inches(1.9)]
table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(0.55), Inches(1.85),
                                     Inches(12.2), Inches(3.9))
tbl = table_shape.table
for i, w in enumerate(col_w):
    tbl.columns[i].width = Emu(int(w / Inches(13.35) * Inches(12.2)))

for j, head in enumerate(headers):
    cell = tbl.cell(0, j)
    cell.text = head
    cell.fill.solid()
    cell.fill.fore_color.rgb = CARD
    for p in cell.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(11)
            r.font.bold = True
            r.font.color.rgb = INK
            r.font.name = "Aptos"
    cell.margin_left = Inches(0.10)
    cell.margin_top = Inches(0.04)
    cell.margin_bottom = Inches(0.04)

for i, row in enumerate(rows, start=1):
    for j, value in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xFB, 0xFA, 0xFE)
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(11)
                r.font.name = "Aptos"
                r.font.bold = j == 0
                r.font.color.rgb = INK if j == 0 else MUTED
        cell.margin_left = Inches(0.10)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)

card(Inches(0.55), Inches(5.95), Inches(12.2), Inches(0.85), fill=BAND)
text(Inches(0.80), Inches(6.06), Inches(11.6), Inches(0.25), "WHY SIX", size=9.5, bold=True, color=TEAL)
text(Inches(0.80), Inches(6.32), Inches(11.7), Inches(0.45),
     "Merge two and something specific breaks: metrics inside the graph make a threshold change a data migration; "
     "evidence inside the graph puts audit on the pricing path. At pilot scale four would work — the boundaries are drawn where they get enforced.",
     size=10.5, color=INK, spacing=1.15)

text(Inches(0.55), Inches(7.08), Inches(9.5), Inches(0.25),
     "Visionet  |  Insurance Knowledge Framework  |  Client proposition", size=9.5, color=MUTED)
foot = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.72), Inches(7.00), Inches(0.32), Inches(0.32))
_strip(foot)
foot.fill.solid()
foot.fill.fore_color.rgb = ACCENT
foot.line.fill.background()
tf = foot.text_frame
tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.CENTER
r = p.add_run()
r.text = "A"
r.font.size = Pt(10)
r.font.bold = True
r.font.color.rgb = WHITE
r.font.name = "Aptos"

slide.notes_slide.notes_text_frame.text = (
    "One boundary per rate of change and owner. The evidence store is the weakest in the POC: the contract exists, "
    "the persistence does not. Say that before someone asks."
)

prs.save(OUT)
print("saved", OUT)
