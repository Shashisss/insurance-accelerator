"""Risk assessment orchestration: graph context + rules -> explained score."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ontology import get_ontology
from .rules import evaluate


def _assessment_id(property_id: str, ruleset_version: str, as_of: str) -> str:
    return f"RA::{property_id}::{ruleset_version}::{as_of}"


def _driver_summary(findings: list[dict[str, Any]], limit: int = 3) -> list[str]:
    ranked = sorted((f for f in findings if f["points"] > 0), key=lambda f: f["points"], reverse=True)
    return [f"{f['name']}: {f['evidence']} (+{f['points']})" for f in ranked[:limit]]


def assess_property(store: Any, property_id: str, as_of: str | None = None, persist: bool = True) -> dict[str, Any] | None:
    """The POC's success criterion, as one call.

    Given a property id: connected policy, coverage, claims and risk factors ->
    underwriting rules -> an explained risk assessment.
    """
    context = store.property_360(property_id)
    if context is None:
        return None

    ontology = get_ontology()
    result = evaluate(store, property_id, ontology=ontology, as_of=as_of)
    if result is None:
        return None

    prop = context["property"]
    assessment = {
        "assessment_id": _assessment_id(property_id, result["ruleset_version"], result["as_of"]),
        "property_id": property_id,
        "property_label": f"{prop['address']}, {prop.get('city')} {prop.get('state')}",
        "policy_id": prop["policy_id"],
        "customer_id": (context.get("policy") or {}).get("customer_id"),
        "customer_name": (context.get("customer") or {}).get("name"),
        "score": result["score"],
        "raw_score": result["raw_score"],
        "band": result["band"],
        "decision": result["decision"],
        "ruleset_version": result["ruleset_version"],
        "as_of": result["as_of"],
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "findings": result["findings"],
        "hard_stops": result["hard_stops"],
        "top_drivers": _driver_summary(result["findings"]),
        "context": {
            "property": prop,
            "policy": context.get("policy"),
            "customer": context.get("customer"),
            "coverages": context.get("coverages", []),
            "claims": context.get("claims", []),
        },
    }

    if persist:
        store.save_assessment(assessment)
    return assessment


def assess_all(store: Any, as_of: str | None = None) -> list[dict[str, Any]]:
    out = []
    for prop in store.list_properties():
        assessment = assess_property(store, prop["property_id"], as_of=as_of)
        if assessment:
            out.append(assessment)
    return out


def portfolio_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    by_band: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    for a in assessments:
        by_band[a["band"]] = by_band.get(a["band"], 0) + 1
        by_decision[a["decision"]] = by_decision.get(a["decision"], 0) + 1
    scores = [a["score"] for a in assessments] or [0]
    return {
        "properties": len(assessments),
        "average_score": round(sum(scores) / len(scores), 1),
        "by_band": by_band,
        "by_decision": by_decision,
        "rule_hits": sum(1 for a in assessments for f in a["findings"] if f["points"] > 0),
        "hard_stops": sum(len(a["hard_stops"]) for a in assessments),
    }
