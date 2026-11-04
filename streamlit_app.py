"""Streamlit workbench for the Insurance Ontology Accelerator POC.

Run:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import streamlit as st

from iaa.graph import get_store
from iaa.ingest import map_source_file
from iaa.ontology import get_ontology
from iaa.risk import assess_all, assess_property, portfolio_summary
from iaa.rules import months_ago
from iaa.viz import cypher_for_property, dot_for_book, dot_for_property
from iaa.config import settings

BAND_COLOR = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Decline": "🔴"}

st.set_page_config(page_title="Insurance Ontology Accelerator", page_icon="🏢", layout="wide")

store = get_store()
ontology = get_ontology()
properties = store.list_properties()
labels = {f"{p['property_id']} · {p['address']}, {p.get('city')} {p.get('state')}": p["property_id"] for p in properties}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🏢 Insurance Ontology")
    st.caption(f"Ontology v{ontology.version} · ruleset v{ontology.rule_version}")
    health = store.health()
    if health.get("ok"):
        st.success(f"Graph backend: {health['backend']}")
    else:
        st.error(health)
    st.caption(health.get("note", ""))

    choice = st.selectbox("Property", list(labels), index=0)
    property_id = labels[choice]
    as_of = st.date_input("Assessment date", value=None)
    st.divider()
    st.caption(
        "POC scope: Commercial Property Underwriting Risk Assessment. "
        "Six entities, eight rules, one explained score."
    )

# ---------------------------------------------------------------- assessment
result = assess_property(store, property_id, as_of=str(as_of) if as_of else None)
ctx = result["context"]
prop, policy, customer = ctx["property"], ctx["policy"], ctx["customer"]

st.title("Underwriting risk assessment")
st.caption(f"{prop['address']}, {prop.get('city')} {prop.get('state')} {prop.get('postcode')} · {prop['property_id']}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Risk score", f"{result['score']}/100")
c2.metric("Band", f"{BAND_COLOR[result['band']]} {result['band']}")
c3.metric("Decision", result["decision"])
window_start = months_ago(date.fromisoformat(result["as_of"]), settings.claims_window_months)
c4.metric("Claims (36m)", len([c for c in ctx["claims"] if c["loss_date"] >= window_start]))
c5.metric("Sum insured", f"{prop['sum_insured']:,.0f}")

if result["hard_stops"]:
    for stop in result["hard_stops"]:
        st.error(
            f"**Hard stop {stop['id']}** — {stop['reason'].rstrip('.')}. "
            "Score is not the decision; this property is declined."
        )

st.progress(min(result["score"], 100) / 100, text=f"Score {result['score']} · raw {result['raw_score']}")

st.subheader("Why this score")
st.caption("Every rule, the attributes it read, and the points it contributed. No hidden weights.")
table = pd.DataFrame(
    [
        {
            "Rule": f["rule_id"],
            "Factor": f["name"],
            "Points": f["points"],
            "Status": f["status"],
            "Evidence": f["evidence"],
        }
        for f in result["findings"]
    ]
)
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "Points": st.column_config.NumberColumn(width="small"),
        "Status": st.column_config.TextColumn(width="small"),
    },
)
st.caption("Top drivers: " + " · ".join(result["top_drivers"] or ["no adverse factors"]))

left, right = st.columns([1, 1])
with left:
    st.subheader("Connected context")
    st.markdown(
        f"**Customer** — {customer['name']} ({customer.get('segment')}, {customer.get('region')})\n\n"
        f"**Policy** — {policy['policy_id']}, {policy['policy_type']}, "
        f"{policy['inception_date']} → {policy['expiry_date']}, {policy['status']}, premium {policy['premium']:,.0f}"
    )
    st.markdown("**Coverages**")
    st.dataframe(
        pd.DataFrame([{"Type": c["coverage_type"], "Limit": c["limit"], "Deductible": c["deductible"]} for c in ctx["coverages"]]),
        hide_index=True,
        width="stretch",
    )

with right:
    st.subheader(f"Claims ({len(ctx['claims'])})")
    if ctx["claims"]:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Claim": c["claim_id"], "Date": str(c["loss_date"]), "Peril": c["peril"], "Amount": c["loss_amount"], "Status": c["status"]}
                    for c in ctx["claims"]
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No claims on record.")

# ---------------------------------------------------------------- tabs
st.divider()
tab_graph, tab_portfolio, tab_mapping, tab_ontology, tab_quality = st.tabs(
    ["Graph view", "Portfolio", "Source mapping", "Ontology", "Data quality"]
)

with tab_graph:
    st.caption(
        "Every node and relationship the assessment just walked. Coloured by entity type; "
        "the risk node carries the band. This is the same data the in-memory store holds — "
        "and the same shape as what `scripts/load_neo4j.py` writes into Neo4j."
    )

    one, book = st.tabs([f"This property ({property_id})", "Whole book (customers → policies → properties)"])

    with one:
        st.graphviz_chart(dot_for_property(store, property_id, result), use_container_width=True)

    with book:
        st.graphviz_chart(dot_for_book(store, assess_all(store)), use_container_width=True)

    with st.expander("Node and relationship tables"):
        nodes = [{"id": customer["customer_id"], "label": "Customer", "name": customer["name"]},
                 {"id": policy["policy_id"], "label": "Policy", "name": policy["policy_type"]},
                 {"id": prop["property_id"], "label": "Property", "name": prop["address"]}]
        nodes += [{"id": c["coverage_id"], "label": "Coverage", "name": c["coverage_type"]} for c in ctx["coverages"]]
        nodes += [{"id": c["claim_id"], "label": "Claim", "name": f"{c['peril']} {c['loss_amount']:,.0f}"} for c in ctx["claims"]]
        edges = [("Customer", customer["customer_id"], "BUYS", "Policy", policy["policy_id"]),
                 ("Policy", policy["policy_id"], "COVERS", "Property", prop["property_id"])]
        edges += [("Policy", policy["policy_id"], "HAS_COVERAGE", "Coverage", c["coverage_id"]) for c in ctx["coverages"]]
        edges += [("Property", prop["property_id"], "HAS_CLAIM", "Claim", c["claim_id"]) for c in ctx["claims"]]
        edges += [("Property", prop["property_id"], "HAS_RISK", "RiskAssessment", result["assessment_id"])]

        gc1, gc2 = st.columns(2)
        gc1.markdown("**Nodes**")
        gc1.dataframe(pd.DataFrame(nodes), hide_index=True, width="stretch")
        gc2.markdown("**Relationships**")
        gc2.dataframe(
            pd.DataFrame([{"from_label": a, "from": b, "rel": c, "to_label": d, "to": e} for a, b, c, d, e in edges]),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Export — Graphviz DOT / Cypher"):
        e1, e2 = st.columns(2)
        e1.markdown("**Graphviz DOT**")
        e1.code(dot_for_property(store, property_id, result), language="dot")
        e2.markdown("**Cypher (paste into Neo4j Browser)**")
        e2.code(cypher_for_property(store, property_id), language="cypher")
        st.download_button(
            "Download this property as Cypher",
            data=cypher_for_property(store, property_id),
            file_name=f"{property_id}.cypher",
            mime="text/plain",
        )

with tab_portfolio:
    assessments = assess_all(store)
    summary = portfolio_summary(assessments)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Properties", summary["properties"])
    m2.metric("Average score", summary["average_score"])
    m3.metric("Refer / decline", summary["by_decision"].get("Refer to underwriter", 0) + summary["by_decision"].get("Decline", 0))
    m4.metric("Hard stops", summary["hard_stops"])

    frame = pd.DataFrame(
        [
            {
                "Property": a["property_id"],
                "Address": a["property_label"],
                "Customer": a.get("customer_name"),
                "Score": a["score"],
                "Band": a["band"],
                "Decision": a["decision"],
                "Top driver": a["top_drivers"][0] if a["top_drivers"] else "none",
            }
            for a in assessments
        ]
    ).sort_values("Score", ascending=False)
    st.dataframe(frame, hide_index=True, width="stretch")
    st.bar_chart(frame.set_index("Property")["Score"])

with tab_mapping:
    st.caption("Raw insurer schedule extract mapped onto the canonical Property entity via the ontology's `source_mapping`.")
    raw_path = Path("data/source/property_schedule_raw.csv")
    st.markdown("**Raw source (first rows)**")
    st.dataframe(pd.read_csv(raw_path).head(4), hide_index=True, width="stretch")
    mapped, issues = map_source_file(raw_path)
    st.markdown(f"**Mapped to canonical model** — {len(mapped)} rows accepted, {len(issues)} issue(s)")
    st.dataframe(pd.DataFrame(mapped).head(8), hide_index=True, width="stretch")
    if issues:
        st.markdown("**Issues**")
        st.dataframe(pd.DataFrame([i.as_dict() for i in issues]), hide_index=True, width="stretch")

with tab_ontology:
    onto = ontology.describe()
    st.markdown(f"**{onto['domain']}** · version {onto['version']} · ruleset {onto['rule_version']}")
    for name, spec in onto["entities"].items():
        with st.expander(f"{name} ({len(spec['attributes'])} attributes)"):
            st.caption(spec["definition"])
            st.dataframe(
                pd.DataFrame(
                    [{"Attribute": a["name"], "Type": a["type"], "Required": a["required"], "Definition": a["definition"]} for a in spec["attributes"]]
                ),
                hide_index=True,
                width="stretch",
            )
    st.markdown("**Relationships**")
    st.dataframe(
        pd.DataFrame(
            [{"Relationship": r["name"], "From": r["from"], "To": r["to"], "Cardinality": r["cardinality"], "Definition": r["definition"]} for r in onto["relationships"]]
        ),
        hide_index=True,
        width="stretch",
    )

with tab_quality:
    ds = getattr(store, "dataset", None)
    if ds is None:
        st.info("Data quality issues are shown for the embedded backend. Neo4j runs the same validation in `scripts/load_neo4j.py`.")
    else:
        counts = ds.counts()
        st.dataframe(pd.DataFrame([{"Entity": k, "Records": v} for k, v in counts.items()]), hide_index=True, width="stretch")
        if ds.issues:
            st.dataframe(pd.DataFrame([i.as_dict() for i in ds.issues]), hide_index=True, width="stretch")
        else:
            st.success("No validation or referential integrity issues in the canonical dataset.")

st.divider()
st.caption(
    "Score = capped sum of rule points. Bands: <25 Low · 25–44 Medium · 45–64 High · ≥65 or hard stop Decline. "
    "Neo4j connects the insurance information; the rules and actuarial calculations stay separate."
)
