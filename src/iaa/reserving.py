"""Claims reserving and IBNR — use case 2 of the framework.

Ultimate = incurred × the approved development factor for the claim's maturity
band and segment. The two valuations differ in three ways, and the value of the
model is that the difference is *decomposed*: paid runoff, reserve
strengthening, and the factor selection itself.

That decomposition is what turns "+15%" from a number into an explanation.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .config import settings

BANDS = [3, 6, 9, 12, 999]


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def _d(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def band_of(accident: date, valuation: date) -> int:
    months = (valuation.year - accident.year) * 12 + (valuation.month - accident.month)
    for i, band in enumerate(BANDS):
        if months < band:
            return i
    return len(BANDS) - 1


@dataclass
class ClaimsBook:
    claims: list[dict[str, Any]] = field(default_factory=list)
    spec: dict[str, Any] = field(default_factory=dict)

    # --- lookups -----------------------------------------------------
    @property
    def valuations(self) -> list[dict[str, Any]]:
        return self.spec["valuations"]

    def valuation(self, valuation_id: str) -> dict[str, Any]:
        return next(v for v in self.valuations if v["valuation_id"] == valuation_id)

    def factors(self, valuation_id: str) -> dict[str, list[float]]:
        return self.spec["factors"][self.valuation(valuation_id)["factor_version"]]

    def rules(self) -> dict[str, Any]:
        return self.spec["rules"]

    def band_factor(self, valuation_id: str, segment: str, accident: date, as_of: date) -> float:
        return self.factors(valuation_id)[segment][band_of(accident, as_of)]

    # --- per-claim view ---------------------------------------------
    def incurred(self, claim: dict[str, Any], valuation_id: str) -> float:
        if valuation_id == "2026-12":
            return claim["paid_dec"] + claim["case_dec"]
        return claim["paid_mar"] + claim["case_mar"]

    def ultimate(self, claim: dict[str, Any], valuation_id: str) -> float:
        as_of = _d(self.valuation(valuation_id)["as_of"])
        return self.incurred(claim, valuation_id) * self.band_factor(
            valuation_id, claim["segment"], claim["accident_date"], as_of)


def load_book(data_dir: Path | None = None, spec_path: Path | None = None) -> ClaimsBook:
    data_dir = Path(data_dir or settings.data_dir) / "claims"
    spec_path = Path(spec_path or settings.ontology_path).with_name("claims_ontology.yaml")
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    claims = []
    for row in _rows(data_dir / "claims.csv"):
        claims.append({
            "claim_id": row["claim_id"],
            "accident_date": _d(row["accident_date"]),
            "reported_date": _d(row["reported_date"]),
            "vehicle_id": row["vehicle_id"],
            "policy_id": row["policy_id"],
            "segment": row["segment"],
            "peril": row["peril"],
            "paid_dec": float(row["paid_dec"]),
            "case_dec": float(row["case_dec"]),
            "paid_mar": float(row["paid_mar"]),
            "case_mar": float(row["case_mar"]),
            "status_dec": row["status_dec"],
            "status_mar": row["status_mar"],
        })
    return ClaimsBook(claims=claims, spec=spec)


# --------------------------------------------------------------------------
# position at a valuation
# --------------------------------------------------------------------------
def position(book: ClaimsBook, valuation_id: str) -> dict[str, Any]:
    as_of = _d(book.valuation(valuation_id)["as_of"])
    per_segment: dict[str, dict[str, float]] = {}

    paid = case = ultimate = 0.0
    for claim in book.claims:
        p = claim["paid_dec"] if valuation_id == "2026-12" else claim["paid_mar"]
        c = claim["case_dec"] if valuation_id == "2026-12" else claim["case_mar"]
        u = book.ultimate(claim, valuation_id)
        seg = per_segment.setdefault(claim["segment"], {"paid": 0.0, "case": 0.0, "ultimate": 0.0, "claims": 0})
        seg["paid"] += p
        seg["case"] += c
        seg["ultimate"] += u
        seg["claims"] += 1
        paid += p
        case += c
        ultimate += u

    incurred = paid + case
    by_segment = [
        {
            "segment": name,
            "claims": int(v["claims"]),
            "paid": round(v["paid"], 2),
            "case": round(v["case"], 2),
            "incurred": round(v["paid"] + v["case"], 2),
            "ultimate": round(v["ultimate"], 2),
            "ibnr": round(v["ultimate"] - v["paid"] - v["case"], 2),
        }
        for name, v in sorted(per_segment.items())
    ]

    return {
        "valuation_id": valuation_id,
        "as_of": as_of.isoformat(),
        "factor_version": book.valuation(valuation_id)["factor_version"],
        "claims": len(book.claims),
        "paid": round(paid, 2),
        "case": round(case, 2),
        "incurred": round(incurred, 2),
        "ultimate": round(ultimate, 2),
        "ibnr": round(ultimate - incurred, 2),
        "case_to_incurred": round(case / incurred, 4) if incurred else 0.0,
        "by_segment": by_segment,
    }


# --------------------------------------------------------------------------
# development between two valuations, decomposed
# --------------------------------------------------------------------------
def _incurred(claim: dict[str, Any], valuation_id: str) -> float:
    return (claim["paid_dec"] + claim["case_dec"]) if valuation_id == "2026-12" else (
        claim["paid_mar"] + claim["case_mar"])


def development(book: ClaimsBook, baseline: str = "2026-12", revised: str = "2027-03") -> dict[str, Any]:
    """Ultimate movement, attributed to three named drivers.

    Ultimate = incurred x selected factor. Between two valuations three things
    move, and they are separable:

      1. incurred movement   — payments made and reserves changed
      2. selection change    — the approved factor table changed (F-2026.12 -> F-2027.03)
      3. maturity            — claims rolled into older bands, where factors are lower

    The three sum exactly to the change; any residual is reported, not hidden.
    """
    base = position(book, baseline)
    rev = position(book, revised)
    base_as_of = _d(book.valuation(baseline)["as_of"])
    rev_as_of = _d(book.valuation(revised)["as_of"])

    incurred_move = selection_change = maturity = 0.0
    for claim in book.claims:
        incurred_dec = _incurred(claim, baseline)
        incurred_mar = _incurred(claim, revised)
        band_dec = band_of(claim["accident_date"], base_as_of)
        band_rev = band_of(claim["accident_date"], rev_as_of)

        f_dec = book.factors(baseline)[claim["segment"]][band_dec]
        f_new_same_band = book.factors(revised)[claim["segment"]][band_dec]
        f_new = book.factors(revised)[claim["segment"]][band_rev]

        incurred_move += (incurred_mar - incurred_dec) * f_dec
        selection_change += incurred_mar * (f_new_same_band - f_dec)
        maturity += incurred_mar * (f_new - f_new_same_band)

    change = rev["ultimate"] - base["ultimate"]
    change_pct = change / base["ultimate"] if base["ultimate"] else 0.0

    rules = book.rules()
    threshold = next(r for r in rules["items"] if r["id"] == "CR1_DEVELOPMENT_THRESHOLD")["threshold"]

    drivers = [
        {"driver": "Incurred movement", "impact": round(incurred_move, 2),
         "note": "payments made and case reserves held at the revised valuation"},
        {"driver": "Selection change", "impact": round(selection_change, 2),
         "note": f"{book.valuation(baseline)['factor_version']} → {book.valuation(revised)['factor_version']} on the same bands"},
        {"driver": "Maturity", "impact": round(maturity, 2),
         "note": "claims rolled into older bands, where factors are lower"},
    ]

    return {
        "baseline": base,
        "revised": rev,
        "change": round(change, 2),
        "change_pct": round(change_pct, 4),
        "alert": change_pct >= threshold,
        "threshold": threshold,
        "drivers": drivers,
        "reconciled": round(sum(d["impact"] for d in drivers) - change, 2),
    }


def top_movements(book: ClaimsBook, baseline: str = "2026-12", revised: str = "2027-03", limit: int = 6) -> list[dict[str, Any]]:
    rows = []
    for claim in book.claims:
        before = book.ultimate(claim, baseline)
        after = book.ultimate(claim, revised)
        rows.append({
            "claim_id": claim["claim_id"],
            "segment": claim["segment"],
            "accident_date": claim["accident_date"].isoformat(),
            "ultimate_before": round(before, 2),
            "ultimate_after": round(after, 2),
            "change": round(after - before, 2),
            "change_pct": round((after - before) / before, 4) if before else 0.0,
        })
    return sorted(rows, key=lambda r: r["change"], reverse=True)[:limit]


def assess(book: ClaimsBook) -> dict[str, Any]:
    dev = development(book)
    rules = []
    for item in book.rules()["items"]:
        if item["id"] == "CR1_DEVELOPMENT_THRESHOLD":
            value = dev["change_pct"]
            breached = value >= item["threshold"]
        elif item["id"] == "CR2_CASE_COVERAGE":
            value = dev["revised"]["case_to_incurred"]
            breached = value < item["threshold"]
        else:  # unknown rule: surfaced, never silently passed as zero
            value = None
            breached = False
        rules.append({
            "rule_id": item["id"], "name": item["name"], "metric": item["metric"],
            "actual": round(value, 4) if value is not None else None, "threshold": item["threshold"],
            "operator": item["operator"],
            "breached": breached, "decision": item["on_breach"] if breached else "pass",
            "rationale": item["rationale"],
        })

    decision = ("Flag adverse development for actuarial review; validate IBNR and reserve adequacy before sign-off"
                if dev["alert"] else "Movement within tolerance; reserves may be signed off")
    return {
        "valuation_baseline": dev["baseline"]["valuation_id"],
        "valuation_revised": dev["revised"]["valuation_id"],
        "baseline": dev["baseline"],
        "revised": dev["revised"],
        "change": dev["change"],
        "change_pct": dev["change_pct"],
        "threshold": dev["threshold"],
        "drivers": dev["drivers"],
        "reconciled": dev["reconciled"],
        "rules": rules,
        "alert": dev["alert"],
        "decision": decision,
        "top_movements": top_movements(book),
    }
