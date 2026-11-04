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
