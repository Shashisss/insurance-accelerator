"""FastAPI service — the thin API layer over graph + rules.

Run:  uvicorn iaa.api:app --reload --port 8000   (from src/, with PYTHONPATH=src)
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from .graph import get_store
from .ontology import get_ontology
from .risk import assess_all, assess_property, portfolio_summary

app = FastAPI(
    title="Insurance Ontology Accelerator (POC)",
    version="0.1.0",
    description="Commercial property underwriting risk assessment over a small insurance graph.",
)


@app.get("/health")
def health() -> dict[str, Any]:
    store = get_store()
    ontology = get_ontology()
    return {
        "status": "ok",
        "ontology_version": ontology.version,
        "ruleset_version": ontology.rule_version,
        "graph": store.health(),
    }


@app.get("/ontology")
def ontology() -> dict[str, Any]:
    return get_ontology().describe()


@app.get("/rules")
def rules() -> dict[str, Any]:
    onto = get_ontology()
    return {
        "summary": onto.scoring_summary(),
        "rules": onto.rule_catalogue(),
        "hard_stops": onto.hard_stops,
    }


@app.get("/properties")
def properties() -> dict[str, Any]:
    store = get_store()
    rows = []
    for prop in store.list_properties():
        assessment = assess_property(store, prop["property_id"], persist=False)
        rows.append(
            {
                "property_id": prop["property_id"],
                "address": prop["address"],
                "city": prop.get("city"),
                "state": prop.get("state"),
                "occupancy": prop.get("occupancy"),
                "construction_type": prop.get("construction_type"),
                "policy_id": prop["policy_id"],
                "score": assessment["score"] if assessment else None,
                "band": assessment["band"] if assessment else None,
                "decision": assessment["decision"] if assessment else None,
            }
        )
    return {"count": len(rows), "properties": rows}


@app.get("/portfolio")
def portfolio() -> dict[str, Any]:
    store = get_store()
    assessments = assess_all(store)
    return {"summary": portfolio_summary(assessments), "assessments": assessments}


@app.get("/properties/{property_id}")
def property_360(property_id: str) -> dict[str, Any]:
    context = get_store().property_360(property_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Unknown property {property_id}")
    return context


@app.get("/properties/{property_id}/assessment")
def assessment(property_id: str, as_of: str | None = None) -> dict[str, Any]:
    result = assess_property(get_store(), property_id, as_of=as_of)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown property {property_id}")
    return result


@app.get("/properties/{property_id}/validation")
def validation(property_id: str, as_of: str | None = None) -> dict[str, Any]:
    """Re-derive every rule's points from the configuration and compare."""
    from .validation import audit_assessment

    result = assess_property(get_store(), property_id, as_of=as_of)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown property {property_id}")
    rows = audit_assessment(get_ontology(), result)
    return {
        "property_id": property_id,
        "ruleset_version": result["ruleset_version"],
        "checks": rows,
        "all_match": all(row["matches"] for row in rows),
    }


# --------------------------------------------------------------------------
# Fleet renewal use case (ABC Express)
# --------------------------------------------------------------------------
def _fleet():
    from .fleet import load_fleet, MetricRegistry

    return load_fleet(), MetricRegistry()


def _as_date(value: str | None):
    from datetime import date

    return date.fromisoformat(value) if value else date(2026, 12, 31)


@app.get("/fleet/policies")
def fleet_policies(as_of: str | None = None, version: str | None = None) -> dict[str, Any]:
    from .fleet import assess_policy

    store, registry = _fleet()
    day = _as_date(as_of)
    rows = []
    for policy in store.list_policies():
        result = assess_policy(store, registry, policy["policy_id"], day, version)
        rows.append({
            "policy_id": policy["policy_id"],
            "entity": result["entity_name"],
            "renewal_date": result["renewal_date"],
            "vehicles": result["metrics"]["vehicles"],
            "loss_ratio": result["metrics"]["loss_ratio"],
            "frequency": result["metrics"]["frequency"],
            "severity": result["metrics"]["severity"],
            "decision": result["decision"],
        })
    return {"as_of": day.isoformat(), "metrics_version": version or "v2", "policies": rows}


@app.get("/fleet/policies/{policy_id}/assessment")
def fleet_assessment(policy_id: str, as_of: str | None = None, version: str | None = None) -> dict[str, Any]:
    from .fleet import assess_policy

    store, registry = _fleet()
    result = assess_policy(store, registry, policy_id, _as_date(as_of), version)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown fleet policy {policy_id}")
    return result


@app.get("/fleet/groups/{group_id}")
def fleet_group(group_id: str, as_of: str | None = None, version: str | None = None) -> dict[str, Any]:
    from .fleet import group_metrics

    store, registry = _fleet()
    if store.group(group_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown group {group_id}")
    day = _as_date(as_of)
    return {
        "group": store.group(group_id),
        "metrics": group_metrics(store, registry, group_id, day, version),
        "policies": [p["policy_id"] for p in store.group_policies(group_id)],
    }


@app.get("/fleet/impact-trace")
def fleet_impact_trace(as_of: str | None = None, from_version: str = "v1", to_version: str = "v2") -> dict[str, Any]:
    from .fleet import impact_trace

    store, registry = _fleet()
    return impact_trace(store, registry, _as_date(as_of), from_version, to_version)


@app.post("/ask")
def ask_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Natural-language question over the same tools the UI uses.

    The assistant may route and phrase, but every number it returns comes from a
    tool call — and answers with unsupported numbers are rejected.
    """
    from .assistant import Toolbox, ask

    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="question is required")
    answer = ask(question, Toolbox())
    body = answer.as_dict()
    body.pop("detail", None)
    return body
