"""POC success criterion: given a property id, the system returns its connected
policy, coverage, claims and risk factors, applies underwriting rules, and
explains the resulting assessment. Deterministically.
"""

from __future__ import annotations

import pytest

from iaa.graph import EmbeddedStore, get_store
from iaa.ingest import load_canonical
from iaa.risk import assess_all, assess_property, portfolio_summary


@pytest.fixture(scope="module")
def store() -> EmbeddedStore:
    return EmbeddedStore(load_canonical())


def test_dataset_loads_without_errors(store):
    assert store.counts() == {"Customer": 8, "Policy": 8, "Property": 12, "Coverage": 18, "Claim": 13}
    errors = [i for i in store.dataset.issues if i.severity == "error"]
    assert errors == [], [e.as_dict() for e in errors]


def test_every_property_reaches_policy_and_customer(store):
    for prop in store.list_properties():
        policy = store.policy(prop["policy_id"])
        assert policy is not None, prop["property_id"]
        assert store.customer(policy["customer_id"]) is not None, prop["policy_id"]


def test_full_assessment_for_one_property(store):
    result = assess_property(store, "PR002", persist=False)

    assert result is not None
    assert result["context"]["customer"]["name"] == "Concord Retail Holdings"
    assert result["context"]["policy"]["policy_id"] == "P1002"
    assert len(result["context"]["coverages"]) == 2
    assert result["findings"] and len(result["findings"]) == 8
    assert 0 <= result["score"] <= 100
    assert result["band"] in {"Low", "Medium", "High", "Decline"}
    assert result["top_drivers"], "every assessment must explain itself"

    # the evidence must name the attributes it actually used
    construction = next(f for f in result["findings"] if f["rule_id"] == "R01_CONSTRUCTION")
    assert construction["inputs"] == {"construction_type": "Frame"}
    assert construction["points"] == 18


def test_hard_stop_declines_even_with_low_points(store):
    # PR005: pre-1950 frame, unsprinklered, and 535k of claims in 36 months
    result = assess_property(store, "PR005", as_of="2026-11-03", persist=False)
    stop_ids = {s["id"] for s in result["hard_stops"]}
    assert {"HS02_OLD_FRAME_UNSPRINKLERED", "HS03_LARGE_RECENT_LOSS"} <= stop_ids
    assert result["band"] == "Decline"
    assert result["decision"] == "Decline"


def test_clean_property_scores_low(store):
    result = assess_property(store, "PR006", as_of="2026-11-03", persist=False)
    assert result["band"] == "Low"
    assert result["decision"] == "Accept"
    assert result["score"] < 25


def test_claims_window_uses_as_of_date(store):
    at_2022 = assess_property(store, "PR002", as_of="2022-12-31", persist=False)
    claims_rule = next(f for f in at_2022["findings"] if f["rule_id"] == "R06_CLAIMS_HISTORY")
    assert claims_rule["inputs"]["claims_36m"] == 1  # the 2022-07 wind claim was still in window

    later = assess_property(store, "PR002", as_of="2026-11-03", persist=False)
    claims_rule = next(f for f in later["findings"] if f["rule_id"] == "R06_CLAIMS_HISTORY")
    assert claims_rule["inputs"]["claims_36m"] == 0


def test_score_is_deterministic(store):
    first = assess_property(store, "PR008", as_of="2026-11-03", persist=False)
    second = assess_property(store, "PR008", as_of="2026-11-03", persist=False)
    assert first["score"] == second["score"]
    assert first["findings"] == second["findings"]
    assert first["assessment_id"] == second["assessment_id"]


def test_portfolio_summary_and_banding(store):
    assessments = assess_all(store, as_of="2026-11-03")
    assert len(assessments) == 12
    summary = portfolio_summary(assessments)
    assert summary["properties"] == 12
    assert summary["by_band"]["Decline"] >= 1
    assert 0 <= summary["average_score"] <= 100
    # bands must be consistent with the configured thresholds
    for a in assessments:
        if a["hard_stops"]:
            assert a["band"] == "Decline"
        elif a["score"] >= 65:
            assert a["band"] == "Decline"
        elif a["score"] >= 45:
            assert a["band"] == "High"
        elif a["score"] >= 25:
            assert a["band"] == "Medium"
        else:
            assert a["band"] == "Low"


def test_assessment_is_persisted_into_the_graph(store):
    result = assess_property(store, "PR001", as_of="2026-11-03")
    context = store.property_360("PR001")
    assert context["assessments"] and context["assessments"][-1]["assessment_id"] == result["assessment_id"]


def test_unknown_property_returns_none(store):
    assert assess_property(store, "NOPE", persist=False) is None


def test_global_store_is_available_without_neo4j(monkeypatch):
    import iaa.graph as graph_module

    monkeypatch.setattr(graph_module, "_STORE", None)
    store = get_store()
    assert store.property("PR001") is not None
