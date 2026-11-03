"""Graph access layer.

Two backends behind one interface:

* `EmbeddedStore` — the dataset held in memory with the same traversal semantics
  as the Cypher queries. Default, so the POC runs anywhere.
* `Neo4jStore` — real Neo4j via the official driver, using `queries.py`.

The risk engine and the API only talk to this interface, so swapping the
backend changes nothing above it. That separation is the point: Neo4j connects
insurance information, it does not become the actuarial engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .config import settings
from .ingest import Dataset, load_canonical
from . import queries


class GraphStore(Protocol):
    backend: str

    def health(self) -> dict[str, Any]: ...
    def counts(self) -> dict[str, int]: ...
    def property(self, property_id: str) -> dict[str, Any] | None: ...
    def policy(self, policy_id: str) -> dict[str, Any] | None: ...
    def customer(self, customer_id: str) -> dict[str, Any] | None: ...
    def coverages_for_policy(self, policy_id: str) -> list[dict[str, Any]]: ...
    def claims_for_property(self, property_id: str) -> list[dict[str, Any]]: ...
    def properties_for_policy(self, policy_id: str) -> list[dict[str, Any]]: ...
    def property_360(self, property_id: str) -> dict[str, Any] | None: ...
    def list_properties(self) -> list[dict[str, Any]]: ...
    def save_assessment(self, assessment: dict[str, Any]) -> None: ...


@dataclass
class EmbeddedStore:
    dataset: Dataset
    backend: str = "embedded-python"

    # --- nodes -------------------------------------------------------
    def property(self, property_id: str) -> dict[str, Any] | None:
        return self.dataset.properties.get(property_id)

    def policy(self, policy_id: str) -> dict[str, Any] | None:
        return self.dataset.policies.get(policy_id)

    def customer(self, customer_id: str) -> dict[str, Any] | None:
        return self.dataset.customers.get(customer_id)

    # --- edges -------------------------------------------------------
    def coverages_for_policy(self, policy_id: str) -> list[dict[str, Any]]:
        return [c for c in self.dataset.coverages.values() if c["policy_id"] == policy_id]

    def claims_for_property(self, property_id: str) -> list[dict[str, Any]]:
        rows = [c for c in self.dataset.claims.values() if c["property_id"] == property_id]
        return sorted(rows, key=lambda c: c["loss_date"])

    def properties_for_policy(self, policy_id: str) -> list[dict[str, Any]]:
        return [p for p in self.dataset.properties.values() if p["policy_id"] == policy_id]

    # --- composed reads ----------------------------------------------
    def property_360(self, property_id: str) -> dict[str, Any] | None:
        prop = self.property(property_id)
        if prop is None:
            return None
        policy = self.policy(prop["policy_id"])
        customer = self.customer(policy["customer_id"]) if policy else None
        return {
            "property": prop,
            "policy": policy,
            "customer": customer,
            "coverages": self.coverages_for_policy(policy["policy_id"]) if policy else [],
            "claims": self.claims_for_property(property_id),
            "assessments": getattr(self, "assessment_index", {}).get(property_id, []),
        }

    def list_properties(self) -> list[dict[str, Any]]:
        return sorted(self.dataset.properties.values(), key=lambda p: p["property_id"])

    def save_assessment(self, assessment: dict[str, Any]) -> None:
        index = getattr(self, "assessment_index", None)
        if index is None:
            index = {}
            object.__setattr__(self, "assessment_index", index)
        index.setdefault(assessment["property_id"], []).append(assessment)

    def counts(self) -> dict[str, int]:
        return self.dataset.counts()

    def health(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "ok": True,
            "counts": self.counts(),
            "issue_count": len(self.dataset.issues),
            "note": "In-memory traversal, same semantics as queries.PROPERTY_360. Set NEO4J_URI to use Neo4j.",
        }


class Neo4jStore:
    backend = "neo4j"

    def __init__(self, driver: Any, database: str) -> None:
        self._driver = driver
        self._database = database

    # --- plumbing ----------------------------------------------------
    def _run(self, cypher: str, **params: Any) -> list[Any]:
        with self._driver.session(database=self._database) as session:
            return [record.data() for record in session.run(cypher, **params)]

    # --- nodes -------------------------------------------------------
    def property(self, property_id: str) -> dict[str, Any] | None:
        rows = self._run("MATCH (p:Property {property_id: $id}) RETURN p", id=property_id)
        return rows[0]["p"] if rows else None

    def policy(self, policy_id: str) -> dict[str, Any] | None:
        rows = self._run("MATCH (p:Policy {policy_id: $id}) RETURN p", id=policy_id)
        return rows[0]["p"] if rows else None

    def customer(self, customer_id: str) -> dict[str, Any] | None:
        rows = self._run("MATCH (c:Customer {customer_id: $id}) RETURN c", id=customer_id)
        return rows[0]["c"] if rows else None

    # --- edges -------------------------------------------------------
    def coverages_for_policy(self, policy_id: str) -> list[dict[str, Any]]:
        rows = self._run(
            "MATCH (:Policy {policy_id: $id})-[:HAS_COVERAGE]->(c:Coverage) RETURN c ORDER BY c.coverage_id",
            id=policy_id,
        )
        return [r["c"] for r in rows]

    def claims_for_property(self, property_id: str) -> list[dict[str, Any]]:
        rows = self._run(
            "MATCH (:Property {property_id: $id})-[:HAS_CLAIM]->(c:Claim) RETURN c ORDER BY c.loss_date",
            id=property_id,
        )
        return [r["c"] for r in rows]

    def properties_for_policy(self, policy_id: str) -> list[dict[str, Any]]:
        rows = self._run(
            "MATCH (:Policy {policy_id: $id})-[:COVERS]->(p:Property) RETURN p ORDER BY p.property_id",
            id=policy_id,
        )
        return [r["p"] for r in rows]

    def property_360(self, property_id: str) -> dict[str, Any] | None:
        rows = self._run(queries.PROPERTY_360, property_id=property_id)
        if not rows:
            return None
        row = rows[0]
        if row.get("property") is None:
            return None
        return {
            "property": row["property"],
            "policy": row.get("policy"),
            "customer": row.get("customer"),
            "coverages": [c for c in (row.get("coverages") or []) if c],
            "claims": [c for c in (row.get("claims") or []) if c],
            "assessments": [row["risk"]] if row.get("risk") else [],
        }

    def list_properties(self) -> list[dict[str, Any]]:
        return [r["p"] for r in self._run(queries.LIST_PROPERTIES)]

    def save_assessment(self, assessment: dict[str, Any]) -> None:
        props = {
            k: v
            for k, v in assessment.items()
            if k not in {"evidence", "hard_stops", "inputs"} and isinstance(v, (str, int, float, bool))
        }
        self._run(
            queries.SAVE_ASSESSMENT,
            property_id=assessment["property_id"],
            assessment_id=assessment["assessment_id"],
            props=props,
        )

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for label in ("Customer", "Policy", "Property", "Coverage", "Claim"):
            rows = self._run(f"MATCH (n:{label}) RETURN count(n) AS c")
            out[label] = int(rows[0]["c"]) if rows else 0
        return out

    def health(self) -> dict[str, Any]:
        try:
            counts = self.counts()
            return {"backend": self.backend, "ok": True, "counts": counts, "note": "Live Neo4j connection."}
        except Exception as exc:  # pragma: no cover - depends on infra
            return {"backend": self.backend, "ok": False, "error": str(exc)}


def build_neo4j_store() -> Neo4jStore:
    from neo4j import GraphDatabase  # imported lazily

    cfg = settings.neo4j
    driver = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))
    driver.verify_connectivity()
    return Neo4jStore(driver, cfg.database)


_STORE: GraphStore | None = None


def get_store(refresh: bool = False) -> GraphStore:
    """Return the configured store, falling back to the embedded backend."""
    global _STORE
    if _STORE is not None and not refresh:
        return _STORE

    if settings.neo4j.configured:
        try:
            _STORE = build_neo4j_store()
            return _STORE
        except Exception as exc:  # pragma: no cover - infra dependent
            store = EmbeddedStore(load_canonical())
            store.backend = "embedded-python (neo4j unavailable: %s)" % exc.__class__.__name__
            _STORE = store
            return _STORE

    _STORE = EmbeddedStore(load_canonical())
    return _STORE
