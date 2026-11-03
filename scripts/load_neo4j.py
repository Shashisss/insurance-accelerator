"""Load the canonical dataset into Neo4j and create the POC graph.

Usage:
    export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=...
    python scripts/load_neo4j.py [--wipe]

The embedded backend needs no such step; this exists so the same model can be
demonstrated on a real Neo4j Community instance.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iaa import queries  # noqa: E402
from iaa.config import settings  # noqa: E402
from iaa.ingest import load_canonical  # noqa: E402


def serialise(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append({k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=settings.neo4j.uri)
    parser.add_argument("--user", default=settings.neo4j.user)
    parser.add_argument("--password", default=settings.neo4j.password)
    parser.add_argument("--database", default=settings.neo4j.database)
    parser.add_argument("--wipe", action="store_true", help="delete existing POC labels first")
    args = parser.parse_args()

    if not args.uri:
        print("NEO4J_URI is not set. The embedded backend needs no load step; set the env vars to load Neo4j.", file=sys.stderr)
        return 2

    from neo4j import GraphDatabase

    ds = load_canonical()
    errors = [i for i in ds.issues if i.severity == "error"]
    if errors:
        print(f"refusing to load: {len(errors)} validation errors", file=sys.stderr)
        for issue in errors[:20]:
            print(f"  {issue.entity} {issue.key}: {issue.attribute} — {issue.message}", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    driver.verify_connectivity()

    with driver.session(database=args.database) as session:
        if args.wipe:
            session.run("MATCH (n) WHERE n:Customer OR n:Policy OR n:Property OR n:Coverage OR n:Claim OR n:RiskAssessment DETACH DELETE n")

        for statement in queries.CONSTRAINTS:
            session.run(statement)

        plans = {
            "Customer": [ds.customers[k] for k in sorted(ds.customers)],
            "Policy": [ds.policies[k] for k in sorted(ds.policies)],
            "Property": [ds.properties[k] for k in sorted(ds.properties)],
            "Coverage": [ds.coverages[k] for k in sorted(ds.coverages)],
            "Claim": [ds.claims[k] for k in sorted(ds.claims)],
        }
        for label, rows in plans.items():
            session.run(queries.LOAD[label], rows=serialise(rows))
            print(f"loaded {len(rows):3d} {label}")

        link_rows = {
            "BUYS": serialise([{"customer_id": p["customer_id"], "policy_id": p["policy_id"]} for p in ds.policies.values()]),
            "COVERS": serialise([{"policy_id": p["policy_id"], "property_id": p["property_id"]} for p in ds.properties.values()]),
            "HAS_COVERAGE": serialise([{"policy_id": c["policy_id"], "coverage_id": c["coverage_id"]} for c in ds.coverages.values()]),
            "HAS_CLAIM": serialise([{"property_id": c["property_id"], "claim_id": c["claim_id"], "policy_id": c["policy_id"]} for c in ds.claims.values()]),
        }
        for _, _, rel, _, _, cypher, _ in queries.LINKS:
            session.run(cypher, rows=link_rows[rel])
            print(f"linked {rel}")

        counts = {}
        for label in ("Customer", "Policy", "Property", "Coverage", "Claim"):
            counts[label] = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
        print("node counts:", counts)

    driver.close()
    print("done — start the API with NEO4J_URI set to use this graph.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
