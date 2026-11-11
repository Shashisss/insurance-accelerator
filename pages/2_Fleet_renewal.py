"""Fleet renewal — the ABC Express scenario from the Insurance Knowledge Framework.

Same engine as the property workbench; adds time-valid vehicle↔policy links,
a group above the entity, and governed metric versions with an impact trace.

Run:  streamlit run streamlit_app.py   (then pick "Fleet renewal" in the sidebar)
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import streamlit as st

from iaa.fleet import (
    MetricRegistry,
    assess_policy,
    group_metrics,
    impact_trace,
    load_fleet,
    policy_metrics,
)

st.set_page_config(page_title="Fleet renewal — ABC Express", page_icon="🚚", layout="wide")

RENEWAL_DATE = date(2027, 1, 1)


@st.cache_resource(show_spinner=False)
def get_fleet():
    return load_fleet(), MetricRegistry()


store, registry = get_fleet()
policies = store.list_policies()
labels = {f"{p['policy_id']} · {p['policy_type']} · renews {p['renewal_date']}": p["policy_id"] for p in policies}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🚚 Fleet renewal")
    st.caption(f"Metrics v{registry.version} · ruleset on file")
    options = list(labels)
    default = next((i for i, label in enumerate(options) if label.startswith("P205")), 0)
    choice = st.selectbox("Policy", options, index=default)
    policy_id = labels[choice]
    as_of = st.date_input("Assessment date", value=date(2026, 12, 31))
    version = st.radio("Loss ratio definition", ["v2", "v1"], horizontal=True,
                       help="v2 adds allocated loss adjustment expense. Switching this is the lifecycle test.")
    st.divider()
    st.caption("Scenario: ABC Express restructured into two entities. 40 vehicles moved off P205. "
               "P205 renews 1 Jan 2027 with 60 vehicles.")

as_of = as_of or date(2026, 12, 31)
result = assess_policy(store, registry, policy_id, as_of, version)
group = result["group"] or {}
group_m = group_metrics(store, registry, group.get("group_id", "G1"), as_of, version)
transfers = store.transfers(date(2025, 12, 31), date(2026, 6, 30))

# ---------------------------------------------------------------- scenario band
st.title("Fleet renewal: context-aware risk assessment")
st.caption(
    f"{result['group_name']} · {result['entity_name']} · {result['policy_label']} · "
    f"renews {result['renewal_date']} · assessed {as_of}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Group fleet", f"{group_m['vehicles']} vehicles", f"{group_m['policies']} policies / 2 entities", delta_color="off")
c2.metric("Transferred off P205", f"{len(transfers)}", "effective 1 Apr 2026", delta_color="off")
c3.metric("P205 fleet at renewal", f"{result['metrics']['vehicles']}", "of 100 before restructuring", delta_color="off")
c4.metric("Metrics version", version.upper(), "v2 includes ALAE" if version == "v2" else "incurred only", delta_color="off")

# ---------------------------------------------------------------- metrics
st.subheader("Three governed metrics")
st.caption("Definitions live in `ontology/fleet_metrics.yaml` — versioned, with a change note and an owner. "
           "The rules reference the metric, never a number.")

m1, m2, m3 = st.columns(3)
m1.metric("Loss ratio", f"{result['metrics']['loss_ratio']:.1%}",
          f"{result['metrics']['loss_ratio_version']} · threshold 60%", delta_color="off")
m2.metric("Frequency", f"{result['metrics']['frequency']:.1f}", "per 100 vehicle-years", delta_color="off")
m3.metric("Severity", f"{result['metrics']['severity']:,.0f}", "per claim", delta_color="off")

with st.expander("Metric inputs — how those three numbers were produced"):
    st.dataframe(
        pd.DataFrame([
            {"Input": "Premium", "Value": f"{result['metrics']['premium']:,.0f}"},
            {"Input": "Incurred (period)", "Value": f"{result['metrics']['incurred']:,.0f}"},
            {"Input": "ALAE", "Value": f"{result['metrics']['alae']:,.0f}"},
            {"Input": f"Numerator ({version})", "Value": f"{result['metrics']['numerator']:,.0f}"},
            {"Input": "Claims in period", "Value": str(result["metrics"]["claim_count"])},
            {"Input": "Vehicles on policy", "Value": str(result["metrics"]["vehicles"])},
            {"Input": "Vehicle-years", "Value": str(result["metrics"]["vehicle_years"])},
            {"Input": "Period", "Value": f"{result['metrics']['period']['from']} → {result['metrics']['period']['to']}"},
        ]),
        hide_index=True, width="stretch",
    )

# ---------------------------------------------------------------- decision
if result["refer"]:
    st.error(f"**{result['decision']}** — FR1 breached at {result['metrics']['loss_ratio']:.1%}. "
             f"{result['underwriter_note']}")
elif result["group_review"]:
    st.warning(f"**{result['decision']}** — {result['underwriter_note']}")
else:
    st.success(f"**{result['decision']}** — {result['underwriter_note']}")

st.subheader("Rules")
st.dataframe(
    pd.DataFrame([
        {
            "Rule": f["rule_id"],
            "Applies when": f"{f['metric']} {'≥' if f['operator'] == 'gte' else '>'} {f['threshold']}",
            "Actual": (f"{f['actual']:.1%}" if f["metric"] == "loss_ratio" else str(f["actual"])),
            "Result": "BREACH" if f["breached"] else "pass",
            "Consequence": f["decision"],
            "Evidence": f["evidence"],
        }
        for f in result["findings"]
    ]),
    hide_index=True, width="stretch",
)

# ---------------------------------------------------------------- evidence
st.subheader("Supporting evidence")
st.caption("History informs the decision; it does not trigger it. Nothing in this table adds points.")
if result["evidence"]:
    st.dataframe(
        pd.DataFrame([
            {"Type": e["kind"].replace("_", " ").title(), "Vehicle": e["vehicle_id"], "Detail": e["text"]}
            for e in result["evidence"]
        ]),
        hide_index=True, width="stretch",
    )
else:
    st.caption("No prior or transferred vehicles in the last three years.")

# ---------------------------------------------------------------- lifecycle
st.divider()
st.subheader("Lifecycle: one change, traced")
trace = impact_trace(store, registry, as_of, "v1", "v2")
st.caption(
    f"Changing the loss ratio definition v1 → v2 moves **{trace['changed']} of {trace['total']}** decisions. "
    "This is the deck's 'trace impact' claim, computed rather than asserted."
)
st.dataframe(
    pd.DataFrame([
        {
            "Policy": r["policy_id"],
            "Loss ratio v1": f"{r['loss_ratio_before']:.1%}",
            "Loss ratio v2": f"{r['loss_ratio_after']:.1%}",
            "Decision v1": r["decision_before"],
            "Decision v2": r["decision_after"],
            "Changed": "yes" if r["changed"] else "no",
        }
        for r in trace["policies"]
    ]),
    hide_index=True, width="stretch",
)

# ---------------------------------------------------------------- graph / temporal
tab_graph, tab_timeline, tab_group, tab_ontology = st.tabs(
    ["Graph", "Vehicle timeline", "Group", "Ontology & metrics"]
)

with tab_graph:
    st.caption("Group → entity → policy → vehicle, with time on the vehicle↔policy edge.")
    nodes = [{"id": group.get("group_id"), "type": "Group", "label": group.get("name")}]
    for entity in store.entities.values():
        if entity["group_id"] == group.get("group_id"):
            nodes.append({"id": entity["entity_id"], "type": "LegalEntity", "label": entity["name"]})
    for p in store.group_policies(group.get("group_id", "G1")):
        nodes.append({"id": p["policy_id"], "type": "Policy",
                      "label": f"{p['policy_id']} · renews {p['renewal_date']}"})
    st.dataframe(pd.DataFrame(nodes), hide_index=True, width="stretch")

    st.markdown("**Edges from this policy**")
    vehicles = result["vehicles"]
    st.dataframe(
        pd.DataFrame([
            {"from": policy_id, "rel": "COVERS (valid 2026-04-01 → 2026-12-31)", "to": f"{len(vehicles)} vehicles"},
            {"from": policy_id, "rel": "HOLDS ←", "to": result["entity_name"]},
            {"from": result["entity_name"], "rel": "OWNS ←", "to": result["group_name"]},
        ]),
        hide_index=True, width="stretch",
    )

with tab_timeline:
    vehicle_ids = sorted(store.vehicles)
    pick = st.selectbox("Vehicle", vehicle_ids, index=vehicle_ids.index("V041"))
    history = store.vehicle_history(pick)
    st.dataframe(
        pd.DataFrame([
            {"Policy": h["policy_id"], "From": h["valid_from"].isoformat(),
             "To": h["valid_to"].isoformat(), "Reason": h["transfer_reason"]}
            for h in history
        ]),
        hide_index=True, width="stretch",
    )
    claims = store.claims_for_vehicle(pick)
    if claims:
        st.markdown("**Claims on this vehicle**")
        st.dataframe(
            pd.DataFrame([
                {"Claim": c["claim_id"], "Date": c["loss_date"].isoformat(), "Peril": c["peril"],
                 "Incurred": c["incurred"], "ALAE": c["alae"], "Policy at loss": c["policy_id"]}
                for c in claims
            ]),
            hide_index=True, width="stretch",
        )
    st.caption("The claim follows the vehicle, not the policy. That is why V041's history is visible on P101 today.")

with tab_group:
    st.metric("Group loss ratio", f"{group_m['loss_ratio']:.1%}", f"{group_m['loss_ratio_version']}")
    st.dataframe(
        pd.DataFrame([
            {"Input": "Premium", "Value": f"{group_m['premium']:,.0f}"},
            {"Input": "Incurred", "Value": f"{group_m['incurred']:,.0f}"},
            {"Input": "ALAE", "Value": f"{group_m['alae']:,.0f}"},
            {"Input": "Claims", "Value": str(group_m["claim_count"])},
            {"Input": "Vehicles", "Value": str(group_m["vehicles"])},
        ]),
        hide_index=True, width="stretch",
    )
    st.caption("FR2 reads this number, not the policy's. 150 > 120 — no single policy can see that.")

with tab_ontology:
    st.markdown("**Loss ratio definition history**")
    st.dataframe(
        pd.DataFrame([
            {"Version": v["version"], "Formula": v["formula"], "Effective": v["effective_from"], "Note": v.get("note", "")}
            for v in registry.lineage("loss_ratio")
        ]),
        hide_index=True, width="stretch",
    )
    st.markdown("**Model**")
    st.markdown(
        "`Group → OWNS → LegalEntity → HOLDS → Policy → COVERS (time-valid) → Vehicle → HAS_CLAIM → Claim`  \n"
        "`Claim → CLAIMED_ON → Policy (the policy in force at the loss date)`"
    )

st.divider()
st.caption(
    "Illustrative scenario — synthetic data, not an underwriting policy. "
    "FR1 and FR2 are demonstration rules, not a rate filing."
)
