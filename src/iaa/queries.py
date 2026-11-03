"""Cypher used by the Neo4j backend and the loader script.

The embedded backend implements the same *semantics* in plain Python so the POC
runs with zero infrastructure, but these are the statements that run against a
real Neo4j instance.
"""

CONSTRAINTS = [
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (n:Customer) REQUIRE n.customer_id IS UNIQUE",
    "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (n:Policy) REQUIRE n.policy_id IS UNIQUE",
    "CREATE CONSTRAINT property_id IF NOT EXISTS FOR (n:Property) REQUIRE n.property_id IS UNIQUE",
    "CREATE CONSTRAINT coverage_id IF NOT EXISTS FOR (n:Coverage) REQUIRE n.coverage_id IS UNIQUE",
    "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (n:Claim) REQUIRE n.claim_id IS UNIQUE",
    "CREATE CONSTRAINT assessment_id IF NOT EXISTS FOR (n:RiskAssessment) REQUIRE n.assessment_id IS UNIQUE",
]

LOAD = {
    "Customer": (
        "UNWIND $rows AS row MERGE (n:Customer {customer_id: row.customer_id}) SET n += row"
    ),
    "Policy": (
        "UNWIND $rows AS row MERGE (n:Policy {policy_id: row.policy_id}) SET n += row"
    ),
    "Property": (
        "UNWIND $rows AS row MERGE (n:Property {property_id: row.property_id}) SET n += row"
    ),
    "Coverage": (
        "UNWIND $rows AS row MERGE (n:Coverage {coverage_id: row.coverage_id}) SET n += row"
    ),
    "Claim": (
        "UNWIND $rows AS row MERGE (n:Claim {claim_id: row.claim_id}) SET n += row"
    ),
}

LINKS = [
    (
        "Customer", "customer_id", "BUYS", "Policy", "policy_id",
        """
        UNWIND $rows AS row
        MATCH (a:Customer {customer_id: row.customer_id})
        MATCH (b:Policy {policy_id: row.policy_id})
        MERGE (a)-[:BUYS]->(b)
        """,
        "policies.csv: policy_id, customer_id",
    ),
    (
        "Policy", "policy_id", "COVERS", "Property", "property_id",
        """
        UNWIND $rows AS row
        MATCH (a:Policy {policy_id: row.policy_id})
        MATCH (b:Property {property_id: row.property_id})
        MERGE (a)-[:COVERS]->(b)
        MERGE (b)-[:INSURED_BY]->(a)
        """,
        "properties.csv: property_id, policy_id",
    ),
    (
        "Policy", "policy_id", "HAS_COVERAGE", "Coverage", "coverage_id",
        """
        UNWIND $rows AS row
        MATCH (a:Policy {policy_id: row.policy_id})
        MATCH (b:Coverage {coverage_id: row.coverage_id})
        MERGE (a)-[:HAS_COVERAGE]->(b)
        """,
        "coverages.csv: coverage_id, policy_id",
    ),
    (
        "Property", "property_id", "HAS_CLAIM", "Claim", "claim_id",
        """
        UNWIND $rows AS row
        MATCH (a:Property {property_id: row.property_id})
        MATCH (b:Claim {claim_id: row.claim_id})
        MERGE (a)-[:HAS_CLAIM]->(b)
        MERGE (b)-[:CLAIMED_ON]->(:Policy {policy_id: row.policy_id})
        """,
        "claims.csv: claim_id, property_id, policy_id",
    ),
]

PROPERTY_360 = """
MATCH (p:Property {property_id: $property_id})
OPTIONAL MATCH (p)-[:INSURED_BY]->(pol:Policy)<-[:BUYS]-(c:Customer)
OPTIONAL MATCH (pol)-[:HAS_COVERAGE]->(cov:Coverage)
WITH p, pol, c, collect(DISTINCT cov) AS coverages
OPTIONAL MATCH (p)-[:HAS_CLAIM]->(cl:Claim)
WITH p, pol, c, coverages, collect(DISTINCT cl) AS claims
OPTIONAL MATCH (p)-[:HAS_RISK]->(ra:RiskAssessment)
WITH p, pol, c, coverages, claims, ra
ORDER BY ra.computed_at DESC
RETURN p AS property,
       pol AS policy,
       c AS customer,
       coverages,
       claims,
       collect(DISTINCT ra)[0] AS risk
"""

SAVE_ASSESSMENT = """
MATCH (p:Property {property_id: $property_id})
MERGE (ra:RiskAssessment {assessment_id: $assessment_id})
SET ra += $props
MERGE (p)-[:HAS_RISK]->(ra)
"""

LIST_PROPERTIES = "MATCH (p:Property) RETURN p ORDER BY p.property_id"
