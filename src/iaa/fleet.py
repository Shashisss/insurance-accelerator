"""Fleet renewal use case — the ABC Express scenario.

Same architecture as the property accelerator, three additions the fleet case
needs and property did not:

1. **Time on the edges.** A vehicle↔policy link is an `Assignment` with a valid
   period, so "which fleet did P205 cover on the renewal date" is a query, not an
   assumption. This is what lets the model see 40 vehicles leave.
2. **A group above the entity.** FR2 fires on aggregate fleet size, which no
   single policy can see.
3. **Governed metrics.** Rules reference a metric definition (with a version),
   never a number. Changing v1→v2 is therefore traceable: `impact_trace()` shows
   which decisions move.

Nothing here touches the property model; both run off the same engine package.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import settings
from .ontology import get_ontology

REFERRAL_THRESHOLD = 0.60  # fallback only; the rule file is the source of truth


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class FleetStore:
    backend: str = "csv (fleet)"
    groups: dict[str, dict[str, Any]] = field(default_factory=dict)
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    vehicles: dict[str, dict[str, Any]] = field(default_factory=dict)
    assignments: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)

    # --- nodes -------------------------------------------------------
    def policy(self, policy_id: str) -> dict[str, Any] | None:
        return self.policies.get(policy_id)

    def entity(self, entity_id: str) -> dict[str, Any] | None:
        return self.entities.get(entity_id)

    def group(self, group_id: str) -> dict[str, Any] | None:
        return self.groups.get(group_id)

    def group_of_policy(self, policy_id: str) -> dict[str, Any] | None:
        policy = self.policy(policy_id)
        entity = self.entity(policy["entity_id"]) if policy else None
        return self.group(entity["group_id"]) if entity else None

    def entity_of_policy(self, policy_id: str) -> dict[str, Any] | None:
        policy = self.policy(policy_id)
        return self.entity(policy["entity_id"]) if policy else None

    def list_policies(self) -> list[dict[str, Any]]:
        return sorted(self.policies.values(), key=lambda p: p["policy_id"])

    # --- time-valid edges --------------------------------------------
    def assignment_on(self, vehicle_id: str, as_of: date) -> dict[str, Any] | None:
        for a in self.assignments:
            if a["vehicle_id"] == vehicle_id and a["valid_from"] <= as_of <= a["valid_to"]:
                return a
        return None

    def vehicles_on_policy(self, policy_id: str, as_of: date) -> list[dict[str, Any]]:
        ids = [a["vehicle_id"] for a in self.assignments
               if a["policy_id"] == policy_id and a["valid_from"] <= as_of <= a["valid_to"]]
        return [self.vehicles[v] for v in sorted(set(ids)) if v in self.vehicles]

    def vehicle_history(self, vehicle_id: str) -> list[dict[str, Any]]:
        return sorted((a for a in self.assignments if a["vehicle_id"] == vehicle_id),
                      key=lambda a: a["valid_from"])

    def transfers(self, start: date, end: date) -> list[dict[str, Any]]:
        """Vehicles whose covering policy changed between two dates."""
        out = []
        for vehicle_id in self.vehicles:
            before, after = self.assignment_on(vehicle_id, start), self.assignment_on(vehicle_id, end)
            if before and after and before["policy_id"] != after["policy_id"]:
                out.append({
                    "vehicle_id": vehicle_id,
                    "from_policy": before["policy_id"],
                    "to_policy": after["policy_id"],
                    "effective": after["valid_from"],
                    "reason": after.get("transfer_reason", ""),
                })
        return sorted(out, key=lambda t: t["vehicle_id"])

    # --- claims -------------------------------------------------------
    def claims_for_policy(self, policy_id: str, since: date | None = None,
                          until: date | None = None) -> list[dict[str, Any]]:
        rows = [c for c in self.claims if c["policy_id"] == policy_id]
        if since:
            rows = [c for c in rows if c["loss_date"] >= since]
        if until:
            rows = [c for c in rows if c["loss_date"] <= until]
        return sorted(rows, key=lambda c: c["loss_date"])

    def claims_for_vehicle(self, vehicle_id: str) -> list[dict[str, Any]]:
        return sorted((c for c in self.claims if c["vehicle_id"] == vehicle_id),
                      key=lambda c: c["loss_date"])

    def group_claims(self, group_id: str, since: date | None = None,
                     until: date | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for policy in self.list_policies():
            if (self.group_of_policy(policy["policy_id"]) or {}).get("group_id") == group_id:
                out.extend(self.claims_for_policy(policy["policy_id"], since, until))
        return out

    def group_policies(self, group_id: str) -> list[dict[str, Any]]:
        return [p for p in self.list_policies()
                if (self.group_of_policy(p["policy_id"]) or {}).get("group_id") == group_id]

    def group_vehicle_count(self, group_id: str, as_of: date) -> int:
        seen: set[str] = set()
        for policy in self.group_policies(group_id):
            seen.update(v["vehicle_id"] for v in self.vehicles_on_policy(policy["policy_id"], as_of))
        return len(seen)

    def counts(self) -> dict[str, int]:
        return {
            "Group": len(self.groups),
            "LegalEntity": len(self.entities),
            "Policy": len(self.policies),
            "Vehicle": len(self.vehicles),
            "Assignment": len(self.assignments),
            "Claim": len(self.claims),
        }


def load_fleet(data_dir: Path | None = None) -> FleetStore:
    data_dir = Path(data_dir or settings.data_dir) / "fleet"
    store = FleetStore()

    for row in _rows(data_dir / "groups.csv"):
        row["restructured_on"] = _d(row.get("restructured_on"))
        store.groups[row["group_id"]] = row

    for row in _rows(data_dir / "entities.csv"):
        row["incorporated_on"] = _d(row.get("incorporated_on"))
        store.entities[row["entity_id"]] = row

    for row in _rows(data_dir / "policies.csv"):
        row["inception_date"] = _d(row["inception_date"])
        row["expiry_date"] = _d(row["expiry_date"])
        row["renewal_date"] = _d(row.get("renewal_date"))
        row["premium"] = _f(row["premium"])
        store.policies[row["policy_id"]] = row

    for row in _rows(data_dir / "vehicles.csv"):
        row["year"] = int(row["year"] or 0)
        row["gvw_tonnes"] = _f(row["gvw_tonnes"])
        store.vehicles[row["vehicle_id"]] = row

    for row in _rows(data_dir / "assignments.csv"):
        row["valid_from"] = _d(row["valid_from"])
        row["valid_to"] = _d(row["valid_to"])
        store.assignments.append(row)

    for row in _rows(data_dir / "claims.csv"):
        row["loss_date"] = _d(row["loss_date"])
        row["incurred"] = _f(row["incurred"])
        row["alae"] = _f(row["alae"])
        store.claims.append(row)

    return store


# --------------------------------------------------------------------------
# governed metrics
# --------------------------------------------------------------------------
class MetricRegistry:
    """Metric definitions with versions; the rules never hold a number."""

    def __init__(self, path: Path | None = None) -> None:
        path = Path(path or settings.ontology_path).with_name("fleet_metrics.yaml")
        self.raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.versions: dict[str, list[str]] = {
            name: [v["version"] for v in spec.get("versions", [])]
            for name, spec in self.raw["metrics"].items()
        }

    @property
    def version(self) -> str:
        return str(self.raw.get("version", "0"))

    def current(self, metric: str) -> str:
        return str(self.raw["metrics"][metric].get("current", "v1"))

    def spec(self, metric: str, version: str | None = None) -> dict[str, Any]:
        spec = self.raw["metrics"][metric]
        version = version or self.current(metric)
        entry = next((v for v in spec["versions"] if v["version"] == version), spec["versions"][-1])
        return {"metric": metric, "name": spec["name"], "definition": spec["definition"],
                "unit": spec.get("unit", ""), **entry}

    def lineage(self, metric: str) -> list[dict[str, Any]]:
        return list(self.raw["metrics"][metric]["versions"])


def _period(store: FleetStore, policy_id: str, as_of: date) -> tuple[date, date]:
    policy = store.policy(policy_id)
    start = max(policy["inception_date"], min(a["valid_from"] for a in store.assignments
                                             if a["policy_id"] == policy_id))
    end = min(as_of, policy["expiry_date"])
    return start, end


def policy_metrics(store: FleetStore, registry: MetricRegistry, policy_id: str,
                   as_of: date, version: str | None = None) -> dict[str, Any]:
    """Compute the three governed metrics for one policy at a point in time."""
    policy = store.policy(policy_id)
    version = version or registry.current("loss_ratio")
    start, end = _period(store, policy_id, as_of)

    vehicles = store.vehicles_on_policy(policy_id, as_of)
    claims = [c for c in store.claims_for_policy(policy_id, since=start, until=end)]
    incurred = sum(c["incurred"] for c in claims)
    alae = sum(c.get("alae", 0.0) for c in claims)

    days = max((end - start).days, 1)
    vehicle_years = len(vehicles) * days / 365.25
    numerator = incurred + (alae if version == "v2" else 0.0)

    loss_ratio = numerator / policy["premium"] if policy["premium"] else 0.0
    frequency = (len(claims) / vehicle_years * 100) if vehicle_years else 0.0
    severity = (incurred / len(claims)) if claims else 0.0

    return {
        "policy_id": policy_id,
        "as_of": as_of.isoformat(),
        "period": {"from": start.isoformat(), "to": end.isoformat(), "days": days},
        "loss_ratio_version": version,
        "loss_ratio": round(loss_ratio, 4),
        "frequency": round(frequency, 2),
        "severity": round(severity, 2),
        "premium": policy["premium"],
        "incurred": incurred,
        "alae": alae,
        "numerator": numerator,
        "claim_count": len(claims),
        "vehicles": len(vehicles),
        "vehicle_years": round(vehicle_years, 2),
    }


def group_metrics(store: FleetStore, registry: MetricRegistry, group_id: str,
                  as_of: date, version: str | None = None) -> dict[str, Any]:
    version = version or registry.current("loss_ratio")
    policies = store.group_policies(group_id)
    premium = sum(p["premium"] for p in policies)
    incurred = alae = 0.0
    claims = 0
    for policy in policies:
        start, end = _period(store, policy["policy_id"], as_of)
        rows = store.claims_for_policy(policy["policy_id"], since=start, until=end)
        incurred += sum(c["incurred"] for c in rows)
        alae += sum(c.get("alae", 0.0) for c in rows)
        claims += len(rows)
    numerator = incurred + (alae if version == "v2" else 0.0)
    return {
        "group_id": group_id,
        "as_of": as_of.isoformat(),
        "loss_ratio_version": version,
        "loss_ratio": round(numerator / premium, 4) if premium else 0.0,
        "premium": premium,
        "incurred": incurred,
        "alae": alae,
        "claim_count": claims,
        "vehicles": store.group_vehicle_count(group_id, as_of),
        "policies": len(policies),
    }


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------
def _ontology_rules() -> dict[str, Any]:
    path = Path(settings.ontology_path).with_name("fleet_ontology.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]


def evaluate(store: FleetStore, registry: MetricRegistry, policy_id: str,
             as_of: date, version: str | None = None) -> dict[str, Any]:
    policy = store.policy(policy_id)
    if policy is None:
        raise KeyError(policy_id)

    rules = _ontology_rules()
    version = version or registry.current("loss_ratio")
    metrics = policy_metrics(store, registry, policy_id, as_of, version)
    group = store.group_of_policy(policy_id)
    entity = store.entity_of_policy(policy_id)
    group_count = store.group_vehicle_count(group["group_id"], as_of) if group else 0
    group_m = group_metrics(store, registry, group["group_id"], as_of, version) if group else None

    actuals = {"loss_ratio": metrics["loss_ratio"], "group_vehicles": group_count}

    findings = []
    for item in rules["items"]:
        value = actuals[item["metric"]]
        threshold = item["threshold"]
        breached = value >= threshold if item["operator"] == "gte" else value > threshold
        findings.append({
            "rule_id": item["id"],
            "name": item["name"],
            "metric": item["metric"],
            "actual": round(value, 4) if isinstance(value, float) else value,
            "threshold": threshold,
            "operator": item["operator"],
            "breached": breached,
            "decision": item["on_breach"] if breached else "pass",
            "rationale": item["rationale"],
            "evidence": _rule_evidence(item["metric"], value, threshold, metrics, group_m, policy),
        })

    refer = any(f["breached"] and f["decision"] == "refer" for f in findings)
    group_review = any(f["breached"] and f["decision"] == "group_review" for f in findings)

    if refer and group_review:
        decision = "Refer for senior review + group assessment"
    elif refer:
        decision = rules["decisions"]["refer"]
    elif group_review:
        decision = rules["decisions"]["group_review"]
    else:
        decision = rules["decisions"]["accept"]

    return {
        "policy_id": policy_id,
        "as_of": as_of.isoformat(),
        "metrics_version": version,
        "ruleset_version": str(rules["version"]),
        "metrics": metrics,
        "group_metrics": group_m,
        "group": group,
        "entity": entity,
        "findings": findings,
        "decision": decision,
        "refer": refer,
        "group_review": group_review,
        "evidence": _supporting_evidence(store, policy_id, as_of, group),
    }


def _rule_evidence(metric: str, value: Any, threshold: Any, metrics: dict[str, Any],
                   group_m: dict[str, Any] | None, policy: dict[str, Any]) -> str:
    if metric == "loss_ratio":
        return (f"Loss ratio {value:.1%} against a {threshold:.0%} referral threshold "
                f"({metrics['loss_ratio_version']}: {metrics['numerator']:,.0f} / {metrics['premium']:,.0f})")
    if metric == "group_vehicles":
        return f"Group fleet of {value} vehicles against a single-underwriter limit of {threshold}"
    return f"{metric} = {value}"


def _supporting_evidence(store: FleetStore, policy_id: str, as_of: date,
                         group: dict[str, Any] | None) -> list[dict[str, Any]]:
    """History that informs the decision without triggering it.

    Deliberately looks at the fleet *as it is now* and *as it was recently*: a
    vehicle that left this policy last quarter is exactly the thing a renewal
    underwriter needs to see, and a policy-only view would miss it.
    """
    out: list[dict[str, Any]] = []
    moves: dict[tuple[str, str, str], list[str]] = {}
    period_start, _ = _period(store, policy_id, as_of)
    window_start = as_of.replace(year=as_of.year - 3)

    recently_covered = {
        a["vehicle_id"] for a in store.assignments
        if a["policy_id"] == policy_id and a["valid_to"] >= window_start
    }

    for vehicle_id in sorted(recently_covered):
        vehicle = store.vehicles.get(vehicle_id) or {"vehicle_id": vehicle_id}
        history = store.vehicle_history(vehicle_id)
        now = store.assignment_on(vehicle_id, as_of)
        current_here = bool(now and now["policy_id"] == policy_id)

        for claim in store.claims_for_vehicle(vehicle_id):
            if claim["loss_date"] < window_start or claim["loss_date"] > as_of:
                continue
            if period_start <= claim["loss_date"] <= as_of and current_here:
                continue  # already inside the loss ratio
            out.append({
                "kind": "prior_claim",
                "vehicle_id": vehicle_id,
                "claim_id": claim["claim_id"],
                "loss_date": claim["loss_date"].isoformat(),
                "incurred": claim["incurred"],
                "text": (f"{vehicle_id} carried a {claim['incurred']:,.0f} claim on "
                         f"{claim['loss_date'].isoformat()} ({claim.get('description', '')})"),
            })

        if len(history) > 1:
            previous = [h for h in history if h["policy_id"] != policy_id]
            if previous and current_here:
                moves.setdefault(("transferred_in", previous[-1]["policy_id"],
                                  history[-1]["valid_from"].isoformat()), []).append(vehicle_id)
            elif previous and not current_here:
                moves.setdefault(("transferred_out", now["policy_id"] if now else "another policy",
                                  now["valid_from"].isoformat() if now else ""), []).append(vehicle_id)

    # one row per transfer, not one per vehicle — 40 identical rows bury the signal
    for (kind, other_policy, effective), vehicle_ids in sorted(moves.items()):
        sample = ", ".join(vehicle_ids[:3]) + (" …" if len(vehicle_ids) > 3 else "")
        verb = "moved in from" if kind == "transferred_in" else "left this policy for"
        out.append({
            "kind": kind,
            "vehicle_id": sample,
            "count": len(vehicle_ids),
            "other_policy": other_policy,
            "effective": effective,
            "text": (f"{len(vehicle_ids)} vehicle(s) {verb} {other_policy} on {effective}"
                     f" ({sample})"),
        })
    return out


# --------------------------------------------------------------------------
# assessment + lifecycle
# --------------------------------------------------------------------------
def assess_policy(store: FleetStore, registry: MetricRegistry, policy_id: str,
                  as_of: date, version: str | None = None) -> dict[str, Any] | None:
    if store.policy(policy_id) is None:
        return None
    result = evaluate(store, registry, policy_id, as_of, version)
    policy = store.policy(policy_id)
    return {
        **result,
        "assessment_id": f"FR::{policy_id}::{result['ruleset_version']}::{result['metrics_version']}::{as_of}",
        "policy_label": f"{policy['policy_id']} · {policy['policy_type']}",
        "entity_name": (result["entity"] or {}).get("name"),
        "group_name": (result["group"] or {}).get("name"),
        "renewal_date": policy["renewal_date"].isoformat() if policy["renewal_date"] else None,
        "vehicles": [v["vehicle_id"] for v in store.vehicles_on_policy(policy_id, as_of)],
        "underwriter_note": "Underwriter retains the final decision.",
        "computed_at": datetime.now().isoformat(timespec="seconds"),
    }


def impact_trace(store: FleetStore, registry: MetricRegistry, as_of: date,
                 from_version: str = "v1", to_version: str = "v2") -> dict[str, Any]:
    """Which decisions move when the metric definition changes?

    This is the deck's "v1 -> v2, trace impact" claim, computed rather than
    asserted.
    """
    rows = []
    for policy in store.list_policies():
        before = evaluate(store, registry, policy["policy_id"], as_of, from_version)
        after = evaluate(store, registry, policy["policy_id"], as_of, to_version)
        rows.append({
            "policy_id": policy["policy_id"],
            "loss_ratio_before": before["metrics"]["loss_ratio"],
            "loss_ratio_after": after["metrics"]["loss_ratio"],
            "decision_before": before["decision"],
            "decision_after": after["decision"],
            "changed": before["decision"] != after["decision"],
        })
    return {
        "as_of": as_of.isoformat(),
        "from_version": from_version,
        "to_version": to_version,
        "policies": rows,
        "changed": sum(1 for r in rows if r["changed"]),
        "total": len(rows),
    }


def fleet_store() -> FleetStore:
    return load_fleet()
