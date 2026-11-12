"""Claims reserving & IBNR — use case 2 of the framework.

Every claim carries paid and case reserves at two valuation dates. The movement
between them is not reported as one number: it is attributed to incurred
movement, a changed factor selection, and maturity — and the three reconcile.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import streamlit as st

from iaa.reserving import assess, load_book, position

st.set_page_config(page_title="Claims reserving — ABC Insurance", page_icon="📐", layout="wide")

CR = 1e7  # ₹ crore


@st.cache_resource(show_spinner=False)
def get_books():
    return load_book()


book = get_books()
result = assess(book)
base, rev = result["baseline"], result["revised"]

with st.sidebar:
    st.title("📐 Claims reserving")
    st.caption(f"Valuations {base['valuation_id']} → {rev['valuation_id']}")
    st.radio("Valuation view", [base["valuation_id"], rev["valuation_id"]], horizontal=True, key="val")
    st.divider()
    st.caption("Motor portfolio, ABC Insurance. 60 claims, two valuations, one adverse movement.")
    st.caption("Illustrative reserving scenario — not an actuarial opinion.")

st.title("Claims reserving: from 60 claims to a defended IBNR")
st.caption(
    f"Motor portfolio · baseline {base['as_of']} · revised {rev['as_of']} · "
    f"factor selections {base['factor_version']} → {rev['factor_version']}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ultimate, baseline", f"₹{base['ultimate']/CR:.2f} Cr", f"{base['factor_version']}", delta_color="off")
c2.metric("Ultimate, revised", f"₹{rev['ultimate']/CR:.2f} Cr", f"{rev['factor_version']}", delta_color="off")
c3.metric("Development", f"{result['change_pct']:+.1%}", f"₹{result['change']/CR:+.2f} Cr", delta_color="off")
c4.metric("IBNR, revised", f"₹{rev['ibnr']/CR:.2f} Cr", f"case {rev['case_to_incurred']:.0%} of incurred", delta_color="off")

if result["alert"]:
    st.error(f"**{result['decision']}** — development above the {result['threshold']:.0%} tolerance.")
else:
    st.success(result["decision"])

st.subheader("What moved the ultimate")
st.caption("Ultimate = incurred × selected factor. Three things move it, and the three sum to the change.")
drivers = pd.DataFrame([
    {"Driver": d["driver"], "Impact": f"₹{d['impact']/CR:+.2f} Cr", "What it is": d["note"]}
    for d in result["drivers"]
])
st.dataframe(drivers, hide_index=True, width="stretch")
st.caption(
    f"Reconciles to ₹{result['change']/CR:+.2f} Cr "
    f"(residual ₹{result['reconciled']/CR:+.4f} Cr). Nothing is left in an unexplained bucket."
)

st.subheader("By segment")
seg = pd.DataFrame([
    {
        "Segment": s["segment"], "Claims": s["claims"],
        "Paid": f"₹{s['paid']/CR:.2f} Cr", "Case": f"₹{s['case']/CR:.2f} Cr",
        "Incurred": f"₹{s['incurred']/CR:.2f} Cr", "Ultimate": f"₹{s['ultimate']/CR:.2f} Cr",
        "IBNR": f"₹{s['ibnr']/CR:.2f} Cr",
    }
    for s in rev["by_segment"]
])
st.dataframe(seg, hide_index=True, width="stretch")

st.subheader("Rules")
st.dataframe(pd.DataFrame([
    {
        "Rule": r["rule_id"],
        "Applies when": f"{r['metric']} {'<' if r['operator'] == 'lt' else '≥'} {r['threshold']}",
        "Actual": f"{r['actual']:.2%}" if r["actual"] is not None else "not computed",
        "Result": "BREACH" if r["breached"] else "pass", "Consequence": r["decision"],
    }
    for r in result["rules"]
]), hide_index=True, width="stretch")

st.subheader("Drill: largest movements")
st.dataframe(pd.DataFrame([
    {
        "Claim": m["claim_id"], "Segment": m["segment"], "Accident": m["accident_date"],
        "Ultimate before": f"₹{m['ultimate_before']/1e5:.1f}L",
        "Ultimate after": f"₹{m['ultimate_after']/1e5:.1f}L",
        "Change": f"₹{m['change']/1e5:+.1f}L", "%": f"{m['change_pct']:+.1%}",
    }
    for m in result["top_movements"]
]), hide_index=True, width="stretch")

with st.expander("How the arithmetic works — factor selection by maturity band"):
    st.markdown(
        "Ultimate = incurred × factor, where the factor comes from the claim's **maturity band** "
        "at the valuation date (<3, <6, <9, <12, 12+ months) and its **segment**. "
        "The factor table is a versioned, approved object — `F-2026.12` and `F-2027.03`."
    )
    factors = pd.DataFrame([
        {"Segment": seg_name, "F-2026.12": str(book.spec["factors"]["F-2026.12"][seg_name]),
         "F-2027.03": str(book.spec["factors"]["F-2027.03"][seg_name])}
        for seg_name in book.spec["factors"]["F-2026.12"]
    ])
    st.dataframe(factors, hide_index=True, width="stretch")
    st.caption("Bands: <3, <6, <9, <12, 12+ months. Younger claims carry the larger factor.")

st.divider()
st.caption("Illustrative reserving scenario — synthetic claim data, real chain-ladder mechanics.")
