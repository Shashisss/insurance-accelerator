"""Print what the graph actually holds — as a diagram, as data, or as Cypher.

    python scripts/dump_graph.py --property PR005            # Graphviz DOT (paste into graphviz.org or VS Code)
    python scripts/dump_graph.py --property PR005 --format cypher
    python scripts/dump_graph.py --book --format dot
    python scripts/dump_graph.py --property PR005 --format json

Pipe it straight into a file:

    python scripts/dump_graph.py --book > book.dot      # then: dot -Tsvg book.dot -o book.svg
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iaa import assess_all, assess_property, get_store  # noqa: E402
from iaa.viz import cypher_for_property, dot_for_book, dot_for_property  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--property", help="property id, e.g. PR005")
    parser.add_argument("--book", action="store_true", help="customers, policies and properties for the whole book")
    parser.add_argument("--format", choices=["dot", "json", "cypher"], default="dot")
    args = parser.parse_args()

    store = get_store()
    print(f"# backend: {store.health()['backend']}", file=sys.stderr)

    if args.book:
        text = dot_for_book(store, assess_all(store))
        print(text)
        return 0

    if not args.property:
        parser.error("give --property PR005 or --book")

    assessment = assess_property(store, args.property, persist=False)
    if assessment is None:
        print(f"unknown property {args.property}", file=sys.stderr)
        return 1

    if args.format == "dot":
        print(dot_for_property(store, args.property, assessment))
    elif args.format == "cypher":
        print(cypher_for_property(store, args.property))
    else:
        ctx = store.property_360(args.property)
        print(json.dumps({"context": ctx, "assessment": assessment}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
