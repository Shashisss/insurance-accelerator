"""Dynamic pricing and rate adequacy — use case 3.

Premium is not a number in a spreadsheet: it is the output of an exposure, two
trend assumptions, an approved rate version and a target loss ratio. Each of
those is a named object, which is what makes an indication reproducible and
challengeable.

    projected claims   = incurred x (1 + severity trend) x (1 + frequency trend)
    projected ratio    = projected claims / current premium
    indicated premium  = projected claims / target loss ratio
    adequacy ratio     = current premium / indicated premium
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .config import settings


def _d(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_inputs(path: Path | None = None) -> dict[str, Any]:
    path = Path(path or settings.ontology_path).with_name("pricing_inputs.yaml")
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    spec["assumptions"]["effective_from"] = _d(spec["assumptions"].get("effective_from"))
    return spec


def indication(spec: dict[str, Any] | None = None,
               *, severity_trend: float | None = None,
               frequency_trend: float | None = None,
               target_loss_ratio: float | None = None) -> dict[str, Any]:
    spec = spec or load_inputs()
    a = spec["assumptions"]

    sev = a["severity_trend"] if severity_trend is None else severity_trend
    freq = a["frequency_trend"] if frequency_trend is None else frequency_trend
    target = a["target_loss_ratio"] if target_loss_ratio is None else target_loss_ratio

    premium = float(spec["current_premium"])
    incurred = float(spec["incurred_claims"])
    exposure = float(spec["exposure_vehicles"])

    projected_claims = incurred * (1 + sev) * (1 + freq)
    projected_ratio = projected_claims / premium if premium else 0.0
    indicated = projected_claims / target if target else 0.0
    change = (indicated - premium) / premium if premium else 0.0
    adequacy = premium / indicated if indicated else 0.0

    rules = []
    for item in spec["rules"]["items"]:
        value = adequacy if item["metric"] == "adequacy_ratio" else change
        breached = value <= item["threshold"] if item["operator"] == "lt" else value >= item["threshold"]
        rules.append({
            "rule_id": item["id"], "name": item["name"], "metric": item["metric"],
            "actual": round(value, 4), "threshold": item["threshold"], "operator": item["operator"],
            "breached": breached, "decision": item["on_breach"] if breached else "pass",
            "rationale": item["rationale"],
        })

    repriced = any(r["breached"] and r["decision"] == "reprice" for r in rules)
    needs_approval = any(r["breached"] and r["decision"] == "actuarial_and_uw_approval" for r in rules)

    if repriced and needs_approval:
        decision = "Reprice and take to actuarial and underwriting approval"
    elif repriced:
        decision = "Reprice at renewal"
    elif needs_approval:
        decision = "Take the movement to actuarial and underwriting approval"
    else:
        decision = "Renew on current terms"

    return {
        "policy_id": spec["policy_id"],
        "policy_year": spec["policy_year"],
        "rate_version": a["rate_version"],
        "effective_from": a["effective_from"].isoformat() if a["effective_from"] else None,
        "approved_by": a.get("approved_by"),
        "exposure_vehicles": int(exposure),
        "current_premium": round(premium, 2),
        "incurred_claims": round(incurred, 2),
        "current_ratio": round(incurred / premium, 4) if premium else 0.0,
        "severity_trend": sev,
        "frequency_trend": freq,
        "target_loss_ratio": target,
        "projected_claims": round(projected_claims, 2),
        "projected_ratio": round(projected_ratio, 4),
        "indicated_premium": round(indicated, 2),
        "indicated_change": round(change, 4),
        "adequacy_ratio": round(adequacy, 4),
        "premium_per_vehicle_now": round(premium / exposure, 2) if exposure else 0.0,
        "premium_per_vehicle_indicated": round(indicated / exposure, 2) if exposure else 0.0,
        "rules": rules,
        "decision": decision,
        "needs_approval": needs_approval,
    }


def sensitivity(spec: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """What each assumption is actually worth — the challenge any actuary will make."""
    spec = spec or load_inputs()
    a = spec["assumptions"]
    scenarios = [
        ("Both trends (indication)", a["severity_trend"], a["frequency_trend"]),
        ("Severity only", a["severity_trend"], 0.0),
        ("Frequency only", 0.0, a["frequency_trend"]),
        ("No trend", 0.0, 0.0),
    ]
    rows = []
    for name, sev, freq in scenarios:
        result = indication(spec, severity_trend=sev, frequency_trend=freq)
        rows.append({
            "scenario": name,
            "severity": sev,
            "frequency": freq,
            "projected_claims": result["projected_claims"],
            "projected_ratio": result["projected_ratio"],
            "indicated_premium": result["indicated_premium"],
            "indicated_change": result["indicated_change"],
        })
    return rows


def assess(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or load_inputs()
    result = indication(spec)
    result["sensitivity"] = sensitivity(spec)
    return result
