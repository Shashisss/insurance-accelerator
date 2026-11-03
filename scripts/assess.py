"""Assess one property (or the whole book) from the command line.

    python scripts/assess.py PR005
    python scripts/assess.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iaa import assess_all, assess_property, get_store, portfolio_summary  # noqa: E402


def show(result: dict) -> None:
    print(f"\n{result['property_id']}  {result['property_label']}")
    print(f"  customer  {result['customer_name']}   policy {result['policy_id']}")
    print(f"  score     {result['score']}/100  band {result['band']}  decision {result['decision']}")
    for finding in result["findings"]:
        print(f"   +{finding['points']:>2}  {finding['rule_id']:<22} {finding['evidence']}")
    for stop in result["hard_stops"]:
        print(f"   !!  {stop['id']}: {stop['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("property_id", nargs="?", help="e.g. PR005")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true", help="print the full assessment as JSON")
    parser.add_argument("--as-of", default=None, help="assessment date, YYYY-MM-DD")
    args = parser.parse_args()

    store = get_store()
    print(f"graph backend: {store.health()['backend']}")

    if args.all:
        results = assess_all(store, as_of=args.as_of)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
            return 0
        for result in sorted(results, key=lambda r: r["score"], reverse=True):
            show(result)
        summary = portfolio_summary(results)
        print("\nportfolio:", json.dumps(summary, default=str))
        return 0

    if not args.property_id:
        parser.error("give a property id or --all")

    result = assess_property(store, args.property_id, as_of=args.as_of)
    if result is None:
        print(f"unknown property {args.property_id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        show(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
