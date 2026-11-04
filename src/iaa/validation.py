"""Independent re-derivation of a rule's points from the YAML, for checking.

The engine in `rules.py` computes points from the property record. This module
computes the same number from the *rule definition* and the attributes the
engine says it read. If the two disagree, either the configuration or the
implementation has drifted — which is exactly what an underwriter reviewing the
model wants to see, so the app shows the comparison side by side.
"""

from __future__ import annotations

from typing import Any


def _attribute_value(inputs: dict[str, Any]) -> Any:
    for value in inputs.values():
        return value
    return None


def expected_points(rule: dict[str, Any], inputs: dict[str, Any]) -> tuple[int | None, str]:
    """Return (points, note) computed from the rule definition alone."""
    kind = rule.get("kind")

    if kind == "claims":
        count = int(inputs.get("claims_36m") or 0)
        amount = float(inputs.get("amount_36m") or 0)
        severity = rule.get("severity", {})
        points = count * int(rule.get("per_claim_points", 0))
        if severity and amount > float(severity.get("total_amount", 1e18)):
            points += int(severity.get("points", 0))
        points = min(points, int(rule.get("max_points", points)))
        return points, f"{count} claim(s), {amount:,.0f} total"

    if kind == "underinsurance":
        ratio = inputs.get("ratio")
        if ratio is None:
            return None, "no assessed value"
        bands = sorted(rule.get("ratio_thresholds", []), key=lambda b: float(b["min_ratio"]), reverse=True)
        for band in bands:
            if float(ratio) >= float(band["min_ratio"]):
                return int(band["points"]), f"ratio {float(ratio):.0%} ≥ {float(band['min_ratio']):.0%}"
        return 0, f"ratio {float(ratio):.0%}"

    if "bands" in rule:
        value = inputs.get("age") if "age" in inputs else _attribute_value(inputs)
        if value is None:
            return None, "no value"
        bands = sorted(rule["bands"], key=lambda b: b["max"])
        for band in bands:
            if float(value) <= float(band["max"]):
                label = f"≤{band['max']}" if band["max"] < 999 else f"> {bands[-2]['max'] if len(bands) > 1 else 0}"
                return int(band["points"]), f"{value} within {label}"
        return int(bands[-1]["points"]), f"{value} above all bands"

    points_map = {str(k).lower(): int(v) for k, v in rule.get("points", {}).items()}
    value = _attribute_value(inputs)
    if value is None:
        return int(rule.get("default_points", 0)), "missing value → default"
    key = str(bool(value)).lower() if isinstance(value, bool) else str(value).lower()
    if key in points_map:
        return points_map[key], str(value)
    fallback = rule.get("default_points")
    return (int(fallback), f"{value} not in table → default") if fallback is not None else (None, f"{value} not in table")


def audit(rule: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    """Compare what the engine awarded with what the configuration implies."""
    expected, note = expected_points(rule, finding.get("inputs", {}))
    applied = int(finding.get("points", 0))
    return {
        "rule_id": finding.get("rule_id"),
        "applied": applied,
        "expected": expected,
        "matches": expected is None or expected == applied,
        "note": note,
    }


def audit_assessment(ontology: Any, assessment: dict[str, Any]) -> list[dict[str, Any]]:
    rules = {item.id: item.raw for item in ontology.rule_items}
    rows = []
    for finding in assessment.get("findings", []):
        rule = rules.get(finding.get("rule_id"))
        if rule is None:
            continue
        rows.append(audit(rule, finding))
    return rows
