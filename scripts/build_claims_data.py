"""Generate the motor claims triangle for the reserving use case.

    python scripts/build_claims_data.py

Scenario (Insurance Knowledge Framework, use case 2): ABC Insurance motor book,
baseline valuation Dec 2026 at ₹20 Cr ultimate, revised Mar 2027 at ₹23 Cr —
a 15% adverse development flagged for actuarial review.

The claim-level data is synthetic, but the mechanic is real: each claim carries
paid and case reserves at both valuation dates, and ultimate = incurred × the
approved development factor for its maturity band and segment. The generator
calibrates the synthetic amounts so the two valuations land on the deck's
headline, exactly as the fleet generator does for loss ratio.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "claims"

BASELINE = date(2026, 12, 31)
REVISED = date(2027, 3, 31)
TARGET_BASELINE = 20.0  # ₹ crore
TARGET_REVISED = 23.0

# maturity bands in months, worst (youngest) first
BANDS = [3, 6, 9, 12, 999]

# ultimate / incurred selection, by segment
FACTORS = {
    "2026-12": {
        "Own damage": [1.18, 1.08, 1.03, 1.01, 1.00],
        "Third party property": [1.42, 1.24, 1.10, 1.04, 1.00],
        "Third party injury": [1.88, 1.55, 1.28, 1.12, 1.00],
    },
    "2027-03": {
        "Own damage": [1.16, 1.07, 1.02, 1.01, 1.00],
        "Third party property": [1.48, 1.28, 1.12, 1.05, 1.00],
        "Third party injury": [2.05, 1.72, 1.44, 1.26, 1.02],
    },
}

SEGMENTS = ["Own damage", "Third party property", "Third party injury"]
PERILS = {
    "Own damage": ["Collision", "Theft", "Fire", "Flood"],
    "Third party property": ["Third-party property damage"],
    "Third party injury": ["Third-party bodily injury"],
}


def band_factor(segment: str, accident: date, valuation: date, table: dict[str, list[float]]) -> float:
    months = (valuation.year - accident.year) * 12 + (valuation.month - accident.month)
    for band, factor in zip(BANDS, FACTORS[table][segment]):
        if months < band:
            return factor
    return FACTORS[table][segment][-1]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    claims = []
    start = date(2025, 10, 1)
    for i in range(1, 61):
        accident = start + timedelta(days=(i * 11) % 430)
        segment = SEGMENTS[0] if i % 10 in (1, 2, 3, 4, 5, 6) else (
            SEGMENTS[1] if i % 10 in (7, 8) else SEGMENTS[2])
        reported = accident + timedelta(days=12 + (i * 7) % 55)
        if segment == "Own damage":
            base = 45_000 + (i % 7) * 9_000
        elif segment == "Third party property":
            base = 120_000 + (i % 5) * 35_000
        else:
            base = 380_000 + (i % 6) * 190_000
        claims.append({
            "claim_id": f"MC{i:03d}",
            "accident_date": accident,
            "reported_date": reported,
            "vehicle_id": f"V{(i * 7) % 150 + 1:03d}",
            "policy_id": "P205" if i % 3 else "P101",
            "segment": segment,
            "peril": PERILS[segment][i % len(PERILS[segment])],
            "paid_dec": round(base * (0.45 + (i % 4) * 0.08)),
            "case_dec": round(base * (0.55 + (i % 3) * 0.12)),
            "paid_mar": 0,
            "case_mar": 0,
            "status_dec": "Open",
            "status_mar": "Open",
        })

    # development over the quarter: some payment, some reserve movement
    for n, c in enumerate(claims):
        runoff = 0.18 + (n % 5) * 0.03
        c["paid_mar"] = round(c["paid_dec"] + c["case_dec"] * runoff)
        c["case_mar"] = round(c["case_dec"] * (1 - runoff) + c["case_dec"] * 0.04)
        if c["segment"] == "Third party injury":
            c["case_mar"] = round(c["case_mar"] * 1.28)  # reserve strengthening begins

    def ultimate(rows, valuation: date, table: str) -> float:
        total = 0.0
        for c in rows:
            incurred = (c["paid_dec"] + c["case_dec"]) if table == "2026-12" else (c["paid_mar"] + c["case_mar"])
            total += incurred * band_factor(c["segment"], c["accident_date"], valuation, table)
        return total

    # calibrate scale so the baseline lands on ₹20 Cr
    raw = ultimate(claims, BASELINE, "2026-12")
    scale = (TARGET_BASELINE * 1e7) / raw
    for c in claims:
        for key in ("paid_dec", "case_dec", "paid_mar", "case_mar"):
            c[key] = round(c[key] * scale)

    # solve the injury strengthening multiplier that lands the revised on ₹23 Cr
    def revised_with(k: float) -> float:
        for c in claims:
            if c["segment"] == "Third party injury":
                base_case = round(c["case_dec"] * (1 - (0.18 + (claims.index(c) % 5) * 0.03)) * 1.04)
                c["case_mar"] = round(base_case * k)
        return ultimate(claims, REVISED, "2027-03")

    lo, hi = 1.0, 2.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if revised_with(mid) < TARGET_REVISED * 1e7:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2
    revised_with(k)

    fieldnames = ["claim_id", "accident_date", "reported_date", "vehicle_id", "policy_id", "segment",
                  "peril", "paid_dec", "case_dec", "paid_mar", "case_mar", "status_dec", "status_mar"]
    with (OUT / "claims.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(fieldnames)
        for c in claims:
            w.writerow([
                c["claim_id"], c["accident_date"].isoformat(), c["reported_date"].isoformat(),
                c["vehicle_id"], c["policy_id"], c["segment"], c["peril"],
                c["paid_dec"], c["case_dec"], c["paid_mar"], c["case_mar"],
                c["status_dec"], c["status_mar"],
            ])

    base = ultimate(claims, BASELINE, "2026-12")
    rev = ultimate(claims, REVISED, "2027-03")
    print(f"claims          {len(claims)}")
    print(f"baseline ultimate  ₹{base/1e7:.2f} Cr")
    print(f"revised ultimate   ₹{rev/1e7:.2f} Cr  ({(rev/base-1)*100:+.1f}%)")
    print(f"injury strengthening multiplier: {k:.4f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
