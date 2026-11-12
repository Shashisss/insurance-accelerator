"""Pricing & rate adequacy — use case 3 of the framework.

Premium is the output of an exposure, two trend assumptions, a target loss ratio
and an approved rate version. Move any of them and the indication moves — which
is the difference between a price and a number someone made up.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import streamlit as st

from iaa.pricing import assess, indication, load_inputs, sensitivity

st.set_page_config(page_title="Pricing — ABC Express P205", page_icon="💷", layout="wide")


def inr(value: float) -> str:
    """Indian notation: crore, lakh, then rupees."""
    if abs(value) >= 1e7:
        return f"₹{value/1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value/1e5:.2f}L"
    return f"₹{value:,.0f}"

spec = load_inputs()
a = spec["assumptions"]

with st.sidebar:
    st.title("💷 Pricing & adequacy")
    st.caption(f"Rate version {a['rate_version']} · effective {a['effective_from']}")
    severity = st.slider("Severity trend", 0.0, 0.30, float(a["severity_trend"]), 0.01)
    frequency = st.slider("Frequency trend", 0.0, 0.30, float(a["frequency_trend"]), 0.01)
    target = st.slider("Target loss ratio", 0.50, 0.80, float(a["target_loss_ratio"]), 0.01)
    st.divider()
    st.caption("Assumptions are versioned and approved, not typed into a spreadsheet.")
    st.caption("Illustrative pricing scenario — not an approved rate.")

result = indication(spec, severity_trend=severity, frequency_trend=frequency, target_loss_ratio=target)
baseline = indication(spec)

st.title("Pricing: from exposure to an indicated rate")
st.caption(
    f"{result['policy_id']} · {result['exposure_vehicles']} vehicles · rate version {result['rate_version']} · "
    f"effective {result['effective_from']} · approved by {result['approved_by']}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current premium", inr(result["current_premium"]), f"₹{result['premium_per_vehicle_now']:,.0f}/vehicle", delta_color="off")
c2.metric("Projected claims", inr(result["projected_claims"]),
          f"severity {result['severity_trend']:+.0%} · frequency {result['frequency_trend']:+.0%}", delta_color="off")
c3.metric("Projected loss ratio", f"{result['projected_ratio']:.1%}", f"today {result['current_ratio']:.1%}", delta_color="off")
c4.metric("Indicated premium", inr(result["indicated_premium"]),
          f"{result['indicated_change']:+.1%} · adequacy {result['adequacy_ratio']:.1%}", delta_color="off")

if result["needs_approval"]:
    st.error(f"**{result['decision']}** — a {result['indicated_change']:+.1%} movement exceeds the approval threshold.")
else:
    st.warning(f"**{result['decision']}**")

st.subheader("How the indication is built")
st.markdown(
    f"**1.** Incurred claims {inr(result['incurred_claims'])} on premium {inr(result['current_premium'])} "
    f"→ current loss ratio **{result['current_ratio']:.1%}**  \n"
    f"**2.** Trend the claims: × (1 + {result['severity_trend']:.0%} severity) × "
    f"(1 + {result['frequency_trend']:.0%} frequency) → **{inr(result['projected_claims'])}**  \n"
    f"**3.** Hold the target loss ratio of **{result['target_loss_ratio']:.0%}** → "
    f"{inr(result['projected_claims'])} ÷ {result['target_loss_ratio']:.2f} = **{inr(result['indicated_premium'])}**  \n"
    f"**4.** Against today's {inr(result['current_premium'])}: **{result['indicated_change']:+.2%}**, "
    f"rate adequacy **{result['adequacy_ratio']:.1%}**"
)

left, right = st.columns([3, 2])
with left:
    st.subheader("Rules")
    st.dataframe(pd.DataFrame([
        {
            "Rule": r["rule_id"],
            "Applies when": f"{r['metric']} {'≤' if r['operator'] == 'lt' else '≥'} {r['threshold']}",
            "Actual": f"{r['actual']:.2%}", "Result": "BREACH" if r["breached"] else "pass",
            "Consequence": r["decision"],
        }
        for r in result["rules"]
    ]), hide_index=True, width="stretch")

with right:
    st.subheader("Rate adequacy")
    st.progress(min(max(result["adequacy_ratio"], 0.0), 1.0),
                text=f"current premium / indicated premium = {result['adequacy_ratio']:.1%}")
    st.caption("Below 100% the current rate is short of the indication; below 95% the policy is repriced.")

st.subheader("Sensitivity — what each assumption is worth")
st.caption("The first challenge any actuary makes is ‘how much of this is the trend?’ This is that answer.")
sens = pd.DataFrame([
    {
        "Scenario": s["scenario"],
        "Severity": f"{s['severity']:+.0%}", "Frequency": f"{s['frequency']:+.0%}",
        "Projected claims": inr(s["projected_claims"]),
        "Projected ratio": f"{s['projected_ratio']:.1%}",
        "Indicated premium": inr(s["indicated_premium"]),
        "Change": f"{s['indicated_change']:+.1%}",
    }
    for s in sensitivity(spec)
])
st.dataframe(sens, hide_index=True, width="stretch")

with st.expander("Assumptions and versions"):
    st.markdown(
        f"- **Exposure** — {spec['exposure_vehicles']} vehicles, {spec['earned_exposure_vehicle_years']} vehicle-years\n"
        f"- **Current premium** — {inr(spec['current_premium'])}; **incurred claims** — {inr(spec['incurred_claims'])}\n"
        f"- **Severity trend** — {a['severity_trend']:+.0%}; **frequency trend** — {a['frequency_trend']:+.0%}\n"
        f"- **Target loss ratio** — {a['target_loss_ratio']:.0%}\n"
        f"- **Rate version** — {a['rate_version']}, effective {a['effective_from']}, approved by {a['approved_by']}\n"
        f"\nAt the defaults above the indication is {inr(baseline['indicated_premium'])} "
        f"({baseline['indicated_change']:+.1%}), matching the framework deck."
    )

st.divider()
st.caption("Illustrative pricing scenario — synthetic amounts, real mechanics. Not an approved rate.")
