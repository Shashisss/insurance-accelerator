# Insurance Ontology Accelerator — POC

Minimum working proof that a small insurance graph plus a transparent ruleset can answer a
real underwriting question:

> Given a property ID, retrieve its connected policy, coverages, claims and risk factors,
> apply underwriting rules, and explain the resulting risk assessment.

One use case: **Commercial Property Underwriting Risk Assessment**. Six entities, eight rules,
one explained score. No ACORD, no OWL reasoning, no vector store, no GraphRAG, no streaming.

## Quickstart

```bash
cd insurance-accelerator
pip install -r requirements.txt        # fastapi, pyyaml, streamlit, neo4j, pytest

python scripts/assess.py PR005         # explain one property
python scripts/assess.py --all         # whole book, ranked

streamlit run streamlit_app.py         # workbench UI  -> http://localhost:8501
PYTHONPATH=src uvicorn iaa.api:app --port 8000   # API -> http://localhost:8000/docs
pytest -q                              # 20 tests
```

No database is required: the default backend is an in-memory graph with the same traversal
semantics as the Cypher in `src/iaa/queries.py`. Point it at Neo4j when you have one:

```bash
export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=secret
python scripts/load_neo4j.py --wipe
python scripts/assess.py PR005         # now reads from Neo4j
```

The API reports which backend is live at `/health`.

## What is in the box

```
ontology/insurance_ontology.yaml   canonical model + source mapping + ruleset (single source of truth)
data/                              sample book: 8 customers, 8 policies, 12 properties, 18 coverages, 13 claims
data/source/                       deliberately messy insurer schedule extract (for the mapping demo)
src/iaa/ontology.py                model loading
src/iaa/ingest.py                  source -> canonical mapping, coercion, validation, referential integrity
src/iaa/queries.py                 Cypher: constraints, loaders, property_360
src/iaa/graph.py                   GraphStore interface: EmbeddedStore | Neo4jStore
src/iaa/rules.py                   eight underwriting rules + hard stops, all config-driven
src/iaa/risk.py                    assessment orchestration, evidence, portfolio summary
src/iaa/api.py                     FastAPI endpoints
streamlit_app.py                   workbench: score, evidence, graph context, portfolio, mapping, ontology
scripts/load_neo4j.py              load the canonical dataset into Neo4j
scripts/assess.py                  CLI assessment
tests/                             20 tests, including the POC success criterion
```

## Model

| Entity | Key attributes |
| --- | --- |
| Customer | customer_id, name, segment, region |
| Policy | policy_id, customer_id, policy_type, inception/expiry, status, premium, underwriter |
| Property | property_id, policy_id, address, construction, year_built, occupancy, sum_insured, property_value, sprinklered, flood_zone, protection_class |
| Coverage | coverage_id, policy_id, coverage_type, limit, deductible |
| Claim | claim_id, property_id, policy_id, loss_date, peril, loss_amount, status |
| RiskAssessment | assessment_id, property_id, score, band, decision, ruleset_version |

```
(Customer)-[:BUYS]->(Policy)-[:COVERS]->(Property)
(Policy)-[:HAS_COVERAGE]->(Coverage)
(Property)-[:INSURED_BY]->(Policy)
(Property)-[:HAS_CLAIM]->(Claim)-[:CLAIMED_ON]->(Policy)
(Property)-[:HAS_RISK]->(RiskAssessment)
```

## Rules and scoring

Each rule returns points, the attributes it read, and a sentence of evidence. Points are summed
and capped at 100; a hard stop declines regardless of score.

| Rule | Reads | Points |
| --- | --- | --- |
| R01 Construction | Frame 18, Masonry 6, Steel 0 | 0–18 |
| R02 Building age | ≤15 / ≤40 / ≤70 / older | 0/4/10/16 |
| R03 Flood zone | X 0, B/C 2, A/AE 14, V 22 | 0–22 |
| R04 Sprinkler | none installed | 10 |
| R05 Occupancy | Office 0 … Restaurant 12 | 0–12 |
| R06 Claims, 36 months | 5 per claim + 8 if >100k, capped | 0–25 |
| R07 Underinsurance | declared / assessed value | 0–18 |
| R08 Protection class | ≤4 / ≤8 / ≤10 | 0/3/8 |

Bands: **Low** <25 (accept) · **Medium** 25–44 (accept with conditions) · **High** 45–64 (refer) ·
**Decline** ≥65 or any hard stop. Hard stops: V-rated flood zone, pre-1950 frame with no sprinkler,
recent losses above 500k on one property.

The 36-month claim window is computed from the assessment date, so the same book can be re-scored
"as at" any date: `python scripts/assess.py PR002 --as-of 2022-12-31`.

## API

| Endpoint | Returns |
| --- | --- |
| `GET /health` | backend, graph counts, ontology + ruleset version |
| `GET /ontology` | entities, attributes, relationships, thresholds |
| `GET /rules` | ruleset and hard stops |
| `GET /properties` | property list with current score/band |
| `GET /properties/{id}` | 360 view: property, policy, customer, coverages, claims |
| `GET /properties/{id}/assessment?as_of=` | full explained assessment |
| `GET /portfolio` | all assessments + band distribution |

## Second use case: fleet renewal (ABC Express)

The framework deck's fleet scenario, running on the same engine:
`Group → LegalEntity → Policy → Vehicle → Claim`, plus three things the property
case did not need.

| Addition | Why | Where |
| --- | --- | --- |
| **Time-valid edges** | a vehicle↔policy link is an assignment with a valid period, so "which fleet did P205 cover at renewal" is a query | `Assignment` in `ontology/fleet_ontology.yaml`, `FleetStore.vehicles_on_policy(pid, as_of)` |
| **Group above entity** | FR2 fires on 150 vehicles across two entities — invisible to any single policy | `FleetStore.group_vehicle_count()` |
| **Governed metrics** | rules reference a metric definition and version, never a number; changing it is traceable | `ontology/fleet_metrics.yaml`, `impact_trace()` |

```bash
python scripts/build_fleet_data.py      # regenerates the 150-vehicle scenario
streamlit run streamlit_app.py          # sidebar → "Fleet renewal"
python -m pytest tests/test_fleet.py -q # 15 checks
```

The numbers reproduce the deck: loss ratio **50% → 60%** (v2 adds ALAE),
frequency **13.3** per 100 vehicle-years, severity **30,000**, group **150 > 120**,
**40** vehicles transferred, decision **refer + group assessment**. The impact
trace shows both policies changing decision when the metric definition moves
from v1 to v2.

API: `/fleet/policies`, `/fleet/policies/{id}/assessment`, `/fleet/groups/{id}`,
`/fleet/impact-trace`.

## AI layer (optional model, always tools)

`src/iaa/assistant.py` answers questions by calling the same functions the page and the API use —
`assess_policy`, `policy_metrics`, `group_metrics`, `vehicle_history`, `transfers`, `impact_trace`.

- **No model required.** A deterministic planner routes the question and the answer is composed from
  the tool result. That is what the deployed demo runs.
- **Model optional.** Set `IAA_LLM_BASE_URL`, `IAA_LLM_API_KEY`, `IAA_LLM_MODEL` (any
  OpenAI-compatible endpoint) and the model plans and phrases — still over the same tools.
- **The guardrail.** Every number in an answer is checked against a fact sheet built from the tool
  output. Any figure that is not there is grounds for rejection, and the deterministic answer is
  served instead. Tested in `tests/test_assistant.py`.

```bash
curl -s localhost:8000/ask -X POST -H 'content-type: application/json' \
  -d '{"question":"why is P205 referred?"}'
```

The UI entry point (`streamlit_app.py`) is the fleet screen; the property workbench still runs from
`property_app.py`.

## Deliberate non-goals for now

No ACORD/OPIN dependency, no OWL/Protégé reasoning, no separate vector database, no GraphRAG,
no Kafka, no microservices, no custom UI framework.

## Where this goes next

1. Governed ontology repository and versioned rule changes (the YAML is already the seam).
2. Real source onboarding: underwriting workbench extracts, loss runs, geocoding for flood zone.
3. Actuarial loss model behind a separate service — Neo4j connects the insurance information, it
   does not replace the actuarial engine.
4. Production storage/processing (Fabric/Databricks + Delta, Neo4j Aura, API management, Entra ID).
