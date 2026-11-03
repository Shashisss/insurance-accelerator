"""Underwriting rules, read from the ontology YAML.

Each rule is a small deterministic function over the property, its policy, its
claims and the ontology configuration. Every rule returns a finding that carries
the points, the attributes used and a plain-English explanation — the "supporting
evidence" the POC has to show next to the score.

No model calls, no hidden weights: same input, same score, every time.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from .config import settings
from .ontology import Ontology, get_ontology


def as_of_date(override: str | None = None) -> date:
    value = override or settings.as_of
    return date.fromisoformat(value) if value else date.today()


def months_ago(day: date, months: int) -> date:
    month = day.month - months
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    # clamp to the last valid day of the target month
    day_of_month = min(day.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day_of_month)


def finding(rule_id: str, name: str, points: int, status: str, evidence: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "name": name,
        "points": int(points),
        "status": status,  # applied | clear | hard_stop
        "evidence": evidence,
        "inputs": inputs,
    }


def _banded(value: float | None, bands: list[dict[str, Any]]) -> tuple[int, dict[str, Any] | None]:
    if value is None:
        return 0, None
    ordered = sorted(bands, key=lambda b: b.get("max", 0))
    for band in ordered:
        if value <= band.get("max", 0):
            return int(band.get("points", 0)), band
    return int(ordered[-1].get("points", 0)), ordered[-1]


# --------------------------------------------------------------------------
# rule implementations
# --------------------------------------------------------------------------
def rule_construction(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    value = prop.get("construction_type")
    table = {str(k): int(v) for k, v in item["points"].items()}
    pts = table.get(str(value), int(item.get("default_points", 0)))
    worst = max(table.values()) if table else 0
    evidence = f"{value} construction" + (" — heaviest combustible class" if pts == worst and pts > 0 else "")
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"construction_type": value})


def rule_age(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    built = prop.get("year_built")
    age = ctx["as_of"].year - int(built) if built else None
    pts, band = _banded(age, item.get("bands", []))
    evidence = f"Built {built}, {age} years old at assessment date" if age is not None else "Year built missing"
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"year_built": built, "age": age})


def rule_flood(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    zone = str(prop.get("flood_zone") or "").upper()
    table = {str(k).upper(): int(v) for k, v in item["points"].items()}
    pts = table.get(zone, int(item.get("default_points", 0)))
    exposure = {"X": "minimal", "B": "moderate", "C": "moderate", "A": "high", "AE": "high", "V": "very high"}.get(zone, "unknown")
    evidence = f"Flood zone {zone or 'unknown'} — {exposure} flood exposure"
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"flood_zone": zone})


def rule_sprinkler(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    value = prop.get("sprinklered")
    table = {str(k).lower(): int(v) for k, v in item["points"].items()}
    pts = table.get(str(bool(value)).lower(), 0)
    evidence = "Sprinkler system installed" if value else "No automatic sprinkler protection"
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"sprinklered": value})


def rule_occupancy(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    value = str(prop.get("occupancy") or "")
    table = {str(k).lower(): int(v) for k, v in item["points"].items()}
    pts = table.get(value.lower(), int(item.get("default_points", 0)))
    evidence = f"{value or 'Unclassified'} occupancy" + (" — fire load from cooking/guest operations" if value in {"Restaurant", "Hotel"} else "")
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"occupancy": value})


def rule_claims(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    window_start = months_ago(ctx["as_of"], settings.claims_window_months)
    recent = [c for c in ctx["claims"] if c.get("loss_date") and c["loss_date"] >= window_start]
    total = sum(float(c.get("loss_amount") or 0) for c in recent)
    pts = min(
        len(recent) * int(item.get("per_claim_points", 5))
        + int(item.get("severity", {}).get("points", 0) if total > float(item.get("severity", {}).get("total_amount", 1e18)) else 0),
        int(item.get("max_points", 100)),
    )
    if recent:
        perils = ", ".join(sorted({str(c.get("peril")) for c in recent}))
        evidence = f"{len(recent)} claim(s) totalling {total:,.0f} since {window_start.isoformat()} ({perils})"
    else:
        evidence = f"No claims since {window_start.isoformat()}"
    return finding(
        item["id"], item["name"], pts, "applied" if pts else "clear", evidence,
        {"claims_36m": len(recent), "amount_36m": total, "window_start": window_start.isoformat()},
    )


def rule_underinsurance(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    si = prop.get("sum_insured")
    value = prop.get("property_value")
    ratio = (float(si) / float(value)) if si and value else None
    pts = 0
    if ratio is not None:
        for band in sorted(item.get("ratio_thresholds", []), key=lambda b: b["min_ratio"], reverse=True):
            if ratio >= float(band["min_ratio"]):
                pts = int(band["points"])
                break
    evidence = (
        f"Declared {si:,.0f} against assessed {value:,.0f} ({ratio:.0%} of value)"
        if ratio is not None
        else "Assessed property value missing"
    )
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence,
                   {"sum_insured": si, "property_value": value, "ratio": round(ratio, 4) if ratio else None})


def rule_protection_class(item: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    prop = ctx["property"]
    value = prop.get("protection_class")
    pts, _ = _banded(value, item.get("bands", []))
    evidence = f"Fire protection class {value}" if value is not None else "Protection class unknown"
    return finding(item["id"], item["name"], pts, "applied" if pts else "clear", evidence, {"protection_class": value})


RULE_FUNCS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "R01_CONSTRUCTION": rule_construction,
    "R02_BUILDING_AGE": rule_age,
    "R03_FLOOD_ZONE": rule_flood,
    "R04_SPRINKLER": rule_sprinkler,
    "R05_OCCUPANCY": rule_occupancy,
    "R06_CLAIMS_HISTORY": rule_claims,
    "R07_UNDERINSURANCE": rule_underinsurance,
    "R08_PROTECTION_CLASS": rule_protection_class,
}


# --------------------------------------------------------------------------
# hard stops
# --------------------------------------------------------------------------
def evaluate_hard_stops(ontology: Ontology, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    prop = ctx["property"]
    hits: list[dict[str, Any]] = []
    for stop in ontology.hard_stops:
        when = stop.get("when", {})
        ok = True
        for key, expected in when.items():
            if key == "year_built_below":
                ok &= bool(prop.get("year_built") is not None and prop["year_built"] < expected)
            elif key == "claims_36m_total_above":
                window_start = months_ago(ctx["as_of"], settings.claims_window_months)
                total = sum(
                    float(c.get("loss_amount") or 0)
                    for c in ctx["claims"]
                    if c.get("loss_date") and c["loss_date"] >= window_start
                )
                ok &= total > float(expected)
            elif isinstance(expected, bool):
                ok &= bool(prop.get(key)) is expected
            else:
                ok &= str(prop.get(key)) == str(expected)
        if ok:
            hits.append({"id": stop["id"], "reason": stop["reason"]})
    return hits


def evaluate(store: Any, property_id: str, ontology: Ontology | None = None, as_of: str | None = None) -> dict[str, Any] | None:
    """Run the ruleset for one property. Returns findings, score and hard stops."""
    ontology = ontology or get_ontology()
    prop = store.property(property_id)
    if prop is None:
        return None

    policy = store.policy(prop["policy_id"])
    claims = store.claims_for_property(property_id)
    ctx = {
        "property": prop,
        "policy": policy,
        "claims": claims,
        "as_of": as_of_date(as_of),
        "ontology": ontology,
    }

    findings: list[dict[str, Any]] = []
    for item in ontology.rule_items:
        func = RULE_FUNCS.get(item.id)
        if func is None:
            findings.append(finding(item.id, item.name, 0, "clear", "Rule not implemented in this release", {}))
            continue
        findings.append(func(item.raw, ctx))

    hard_stops = evaluate_hard_stops(ontology, ctx)
    raw_score = sum(f["points"] for f in findings)
    max_score = int(ontology.rules.get("scoring", {}).get("max_score", 100))
    score = min(raw_score, max_score)

    thresholds = ontology.thresholds
    if hard_stops or score >= thresholds["decline"]:
        band, decision = "Decline", "Decline"
    elif score >= thresholds["high"]:
        band, decision = "High", "Refer to underwriter"
    elif score >= thresholds["medium"]:
        band, decision = "Medium", "Accept with conditions"
    else:
        band, decision = "Low", "Accept"

    return {
        "property_id": property_id,
        "score": score,
        "raw_score": raw_score,
        "capped": raw_score > max_score,
        "band": band,
        "decision": decision,
        "findings": findings,
        "hard_stops": hard_stops,
        "as_of": ctx["as_of"].isoformat(),
        "ruleset_version": ontology.rule_version,
    }
