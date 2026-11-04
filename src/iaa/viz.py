"""Turn the graph store into pictures and export formats.

Three outputs, all from the same traversal the risk engine uses:

* `dot_for_property()`  — the 360 view of one property as Graphviz DOT
* `dot_for_book()`      — customers → policies → properties, coloured by risk band
* `cypher_for_property()` — CREATE statements for pasting into Neo4j Browser

Nothing here reads the database directly; it asks the store, so it works
identically for the embedded backend and for Neo4j.
"""

from __future__ import annotations

from typing import Any

STYLE = {
    "Customer": ('fillcolor="#dbeafe"', "ellipse"),
    "Policy": ('fillcolor="#fde68a"', "box"),
    "Property": ('fillcolor="#bbf7d0"', "box3d"),
    "Coverage": ('fillcolor="#e9d5ff"', "note"),
    "Claim": ('fillcolor="#fecaca"', "note"),
    "RiskAssessment": ('fillcolor="#c7d2fe"', "component"),
}

BAND_COLOR = {"Low": "#bbf7d0", "Medium": "#fde68a", "High": "#fdba74", "Decline": "#fca5a5"}


def _node(node_id: str, label: str, caption: str, **overrides: str) -> str:
    fill, shape = STYLE.get(label, ('fillcolor="#f3f4f6"', "box"))
    attrs = [
        f'label="{caption}"',
        f"shape={shape}",
        'style="filled,rounded"',
        fill,
        'fontname="Helvetica"',
    ]
    for key, value in overrides.items():
        attrs.append(f'{key}="{value}"')
    return f'  "{node_id}" [{", ".join(attrs)}];'


def _edge(src: str, dst: str, label: str) -> str:
    return f'  "{src}" -> "{dst}" [label="{label}", fontsize=9, color="#6b7280"];'


def dot_for_property(store: Any, property_id: str, assessment: dict[str, Any] | None = None) -> str | None:
    ctx = store.property_360(property_id)
    if ctx is None:
        return None

    prop, policy, customer = ctx["property"], ctx.get("policy"), ctx.get("customer")
    lines = [
        "digraph property {",
        "  rankdir=LR;",
        "  bgcolor=\"transparent\";",
        "  node [fontsize=11, penwidth=0];",
        "  edge [penwidth=1.2];",
    ]

    if customer:
        lines.append(_node(f"C:{customer['customer_id']}", "Customer", f"{customer['name']}\\n{customer.get('segment','')}"))
    if policy:
        lines.append(
            _node(
                f"P:{policy['policy_id']}",
                "Policy",
                f"{policy['policy_id']}\\n{policy['policy_type']}\\n{policy['inception_date']} → {policy['expiry_date']}",
            )
        )
    lines.append(
        _node(
            f"PR:{prop['property_id']}",
            "Property",
            f"{prop['property_id']}\\n{prop['address']}\\n{prop.get('city','')} {prop.get('state','')}",
        )
    )
    for cov in ctx["coverages"]:
        lines.append(_node(f"CV:{cov['coverage_id']}", "Coverage", f"{cov['coverage_type']}\\nlimit {cov['limit']:,.0f}"))
    for claim in ctx["claims"]:
        lines.append(
            _node(
                f"CL:{claim['claim_id']}",
                "Claim",
                f"{claim['peril']}\\n{claim['loss_date']}\\n{claim['loss_amount']:,.0f}",
            )
        )

    band = (assessment or {}).get("band")
    score = (assessment or {}).get("score")
    ra_id = (assessment or {}).get("assessment_id") or f"RA:{property_id}"
    if assessment:
        color = BAND_COLOR.get(band, "#c7d2fe")
        lines.append(
            _node(
                f"RA:{ra_id}",
                "RiskAssessment",
                f"{band} · {score}/100\\n{assessment.get('decision','')}",
                fillcolor=color,
            )
        )

    if customer and policy:
        lines.append(_edge(f"C:{customer['customer_id']}", f"P:{policy['policy_id']}", "BUYS"))
    if policy:
        lines.append(_edge(f"P:{policy['policy_id']}", f"PR:{prop['property_id']}", "COVERS"))
        for cov in ctx["coverages"]:
            lines.append(_edge(f"P:{policy['policy_id']}", f"CV:{cov['coverage_id']}", "HAS_COVERAGE"))
    for claim in ctx["claims"]:
        lines.append(_edge(f"PR:{prop['property_id']}", f"CL:{claim['claim_id']}", "HAS_CLAIM"))
    if assessment:
        lines.append(_edge(f"PR:{prop['property_id']}", f"RA:{ra_id}", "HAS_RISK"))

    lines.append("}")
    return "\n".join(lines)


def dot_for_book(store: Any, assessments: list[dict[str, Any]]) -> str:
    band_by_property = {a["property_id"]: a for a in assessments}
    lines = [
        "digraph book {",
        "  rankdir=LR;",
        "  bgcolor=\"transparent\";",
        "  node [fontsize=10, penwidth=0];",
        "  graph [nodesep=0.25, ranksep=1.1];",
    ]

    properties = store.list_properties()
    policies: dict[str, dict[str, Any]] = {}
    customers: dict[str, dict[str, Any]] = {}
    for prop in properties:
        policy = store.policy(prop["policy_id"])
        if not policy:
            continue
        policies[policy["policy_id"]] = policy
        cust = store.customer(policy["customer_id"])
        if cust:
            customers[cust["customer_id"]] = cust

    for prop in properties:
        a = band_by_property.get(prop["property_id"], {})
        colour = BAND_COLOR.get(a.get("band", ""), "#e5e7eb")
        lines.append(
            _node(
                f"PR:{prop['property_id']}",
                "Property",
                f"{prop['property_id']}\\n{a.get('band','–')} {a.get('score','')}",
                fillcolor=colour,
            )
        )

    for policy in policies.values():
        lines.append(_node(f"P:{policy['policy_id']}", "Policy", f"{policy['policy_id']}\\npremium {policy['premium']:,.0f}"))
    for cust in customers.values():
        lines.append(_node(f"C:{cust['customer_id']}", "Customer", f"{cust['name']}"))

    for policy in policies.values():
        lines.append(_edge(f"C:{policy['customer_id']}", f"P:{policy['policy_id']}", "BUYS"))
    for prop in properties:
        lines.append(_edge(f"P:{prop['policy_id']}", f"PR:{prop['property_id']}", "COVERS"))

    lines.append("}")
    return "\n".join(lines)


def cypher_for_property(store: Any, property_id: str) -> str | None:
    """CREATE statements matching what the loader puts in Neo4j."""
    ctx = store.property_360(property_id)
    if ctx is None:
        return None
    prop, policy, customer = ctx["property"], ctx.get("policy"), ctx.get("customer")

    def clean(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return "'" + str(value).replace("'", "\\'") + "'"

    def props(record: dict[str, Any]) -> str:
        return ", ".join(f"{k}: {clean(v)}" for k, v in record.items() if v is not None)

    lines: list[str] = []
    if customer:
        lines.append(f"CREATE (:Customer {{{props(customer)}}});")
        lines.append(f"CREATE (:Policy {{{props(policy)}}});")
        lines.append(
            f"MATCH (c:Customer {{customer_id: {clean(customer['customer_id'])}}}), "
            f"(p:Policy {{policy_id: {clean(policy['policy_id'])}}}) CREATE (c)-[:BUYS]->(p);"
        )
    else:
        lines.append(f"CREATE (:Policy {{{props(policy)}}});")

    lines.append(f"CREATE (:Property {{{props(prop)}}});")
    lines.append(
        f"MATCH (p:Policy {{policy_id: {clean(prop['policy_id'])}}}), "
        f"(b:Property {{property_id: {clean(prop['property_id'])}}}) "
        f"CREATE (p)-[:COVERS]->(b), (b)-[:INSURED_BY]->(p);"
    )

    for cov in ctx["coverages"]:
        lines.append(f"CREATE (:Coverage {{{props(cov)}}});")
        lines.append(
            f"MATCH (p:Policy {{policy_id: {clean(cov['policy_id'])}}}), "
            f"(v:Coverage {{coverage_id: {clean(cov['coverage_id'])}}}) CREATE (p)-[:HAS_COVERAGE]->(v);"
        )

    for claim in ctx["claims"]:
        lines.append(f"CREATE (:Claim {{{props(claim)}}});")
        lines.append(
            f"MATCH (b:Property {{property_id: {clean(claim['property_id'])}}}), "
            f"(l:Claim {{claim_id: {clean(claim['claim_id'])}}}) CREATE (b)-[:HAS_CLAIM]->(l);"
        )

    return "\n".join(lines)
