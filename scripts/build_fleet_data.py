"""Generate the fleet renewal dataset (the ABC Express scenario from the framework deck).

Deterministic and regenerable:

    python scripts/build_fleet_data.py

Story, exactly as the slide tells it:
  * 2025: ABC Express, one legal entity, 100 vehicles on policy P205.
  * 2026: restructured into two entities — 90 + 60 vehicles, one group of 150.
  * 40 vehicles transfer from P205 to P101 on 2026-04-01 (V041–V080).
  * V041 carries a 5L prior claim; it now sits on P101, not P205.
  * P205 renews 2027-01-01 with 60 vehicles.

Numbers are built so the three governed metrics land on the deck's values:
  loss ratio 50% (v1) -> 60% (v2, incl. ALAE), frequency 13.3 per 100 vehicle-years,
  severity 30,000 per claim.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fleet"

TRANSFER_DATE = "2026-04-01"
CURRENT_FROM = "2026-04-01"
CURRENT_TO = "2026-12-31"
PRIOR_FROM = "2025-04-01"
PRIOR_TO = "2026-03-31"

MAKES = [
    ("Tata", "Ace Gold"), ("Tata", "Intra V30"), ("Ashok Leyland", "Dost+"),
    ("Eicher", "Pro 2049"), ("Mahindra", "Jeeto"), ("Tata", "407"),
]


def vehicles() -> list[dict]:
    rows = []
    for i in range(1, 151):
        make, model = MAKES[i % len(MAKES)]
        rows.append({
            "vehicle_id": f"V{i:03d}",
            "registration": f"MH{12 + (i % 8)}AB{1000 + i}",
            "make": make,
            "model": model,
            "year": 2016 + (i % 9),
            "vehicle_class": "LCV" if i % 5 else "HCV",
            "gvw_tonnes": 3.5 if i % 5 else 7.5,
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    def write(name: str, fieldnames: list[str], rows: list[dict]) -> None:
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{name:22} {len(rows):>4} rows")

    with (OUT / "groups.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["group_id", "name", "segment", "region", "restructured_on"])
        w.writeheader()
        w.writerow({"group_id": "G1", "name": "ABC Express Group", "segment": "Fleet / Transport",
                    "region": "West India", "restructured_on": TRANSFER_DATE})
    print(f"{'groups.csv':22}    1 rows")

    with (OUT / "entities.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["entity_id", "group_id", "name", "type", "incorporated_on"])
        w.writeheader()
        w.writerow({"entity_id": "E1", "group_id": "G1", "name": "ABC Express Logistics Pvt Ltd",
                    "type": "Operating company", "incorporated_on": "2026-03-15"})
        w.writerow({"entity_id": "E2", "group_id": "G1", "name": "ABC Express Transport Pvt Ltd",
                    "type": "Operating company", "incorporated_on": "2026-03-15"})
    print(f"{'entities.csv':22}    2 rows")

    policies = [
        {"policy_id": "P101", "entity_id": "E1", "policy_type": "Commercial Vehicle Fleet",
         "inception_date": CURRENT_FROM, "expiry_date": CURRENT_TO, "status": "Active",
         "premium": 720000, "renewal_date": "2027-01-01", "underwriter": "A. Rivera"},
        {"policy_id": "P205", "entity_id": "E2", "policy_type": "Commercial Vehicle Fleet",
         "inception_date": CURRENT_FROM, "expiry_date": CURRENT_TO, "status": "Renewal due",
         "premium": 360000, "renewal_date": "2027-01-01", "underwriter": "M. Osei"},
    ]
    write("policies.csv", list(policies[0]), policies)

    rows = vehicles()
    write("vehicles.csv", list(rows[0]), rows)

    assignments: list[dict] = []

    def add_assignment(n: int, vehicle_id: str, policy_id: str, start: str, end: str, reason: str) -> None:
        assignments.append({
            "assignment_id": f"A{n:03d}", "vehicle_id": vehicle_id, "policy_id": policy_id,
            "valid_from": start, "valid_to": end, "transfer_reason": reason,
        })

    # 2025: the whole 100-vehicle fleet sits on P205, one entity.
    for i in range(1, 101):
        add_assignment(len(assignments) + 1, f"V{i:03d}", "P205", PRIOR_FROM, PRIOR_TO, "Original schedule")

    # 2026: 60 stay on P205 (V001-V040, V081-V100); 40 transfer to P101 (V041-V080).
    for i in list(range(1, 41)) + list(range(81, 101)):
        add_assignment(len(assignments) + 1, f"V{i:03d}", "P205", CURRENT_FROM, CURRENT_TO, "Retained")
    for i in range(41, 81):
        add_assignment(len(assignments) + 1, f"V{i:03d}", "P101", CURRENT_FROM, CURRENT_TO,
                       f"Transferred from P205 on {TRANSFER_DATE}")
    for i in range(101, 151):
        add_assignment(len(assignments) + 1, f"V{i:03d}", "P101", CURRENT_FROM, CURRENT_TO, "New to P101")

    write("assignments.csv", list(assignments[0]), assignments)

    # Claims: P205 — 6 claims x 30,000 incurred, ALAE 6,000 each (13.3 per 100 vehicle-years).
    claims: list[dict] = []
    p205_dates = ["2026-04-19", "2026-05-28", "2026-06-11", "2026-07-02", "2026-09-09", "2026-10-21"]
    p205_vehicles = ["V003", "V012", "V038", "V085", "V097", "V100"]
    for n, (day, veh) in enumerate(zip(p205_dates, p205_vehicles), start=1):
        claims.append({
            "claim_id": f"CL5{n:02d}", "vehicle_id": veh, "policy_id": "P205", "loss_date": day,
            "peril": "Own damage" if n % 3 else "Third party", "incurred": 30000, "alae": 6000,
            "status": "Closed" if n < 6 else "Open",
            "description": "Minor collision / panel damage" if n % 3 else "Third-party property damage",
        })

    # P101 — 6 claims x 50,000 incurred, ALAE 22,000 each: 300k / 720k = 41.7% (v1), 60% (v2).
    p101_dates = ["2026-04-25", "2026-06-03", "2026-06-29", "2026-08-05", "2026-09-22", "2026-10-30"]
    p101_vehicles = ["V045", "V052", "V069", "V104", "V121", "V140"]
    for n, (day, veh) in enumerate(zip(p101_dates, p101_vehicles), start=1):
        claims.append({
            "claim_id": f"CL1{n:02d}", "vehicle_id": veh, "policy_id": "P101", "loss_date": day,
            "peril": "Own damage", "incurred": 50000, "alae": 22000, "status": "Closed",
            "description": "Collision with roadside barrier",
        })

    # The prior claim that followed V041 out of P205.
    claims.append({
        "claim_id": "CL001", "vehicle_id": "V041", "policy_id": "P205", "loss_date": "2025-08-14",
        "peril": "Third party", "incurred": 500000, "alae": 60000, "status": "Closed",
        "description": "Fatal third-party liability; V041 transferred to P101 on 2026-04-01",
    })

    write("claims.csv", list(claims[0]), claims)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
