"""Fleet renewal use case: the deck's claims, made checkable."""

from __future__ import annotations

from datetime import date

import pytest

from iaa.fleet import (
    MetricRegistry,
    assess_policy,
    group_metrics,
    impact_trace,
    load_fleet,
    policy_metrics,
)

AS_OF = date(2026, 12, 31)


@pytest.fixture(scope="module")
def store():
    return load_fleet()


@pytest.fixture(scope="module")
def registry():
    return MetricRegistry()


# --- the scenario ---------------------------------------------------------
def test_group_holds_one_hundred_and_fifty_vehicles_across_two_entities(store):
    assert store.counts()["Vehicle"] == 150
    assert store.counts()["LegalEntity"] == 2
    assert store.group_vehicle_count("G1", AS_OF) == 150
    assert {p["entity_id"] for p in store.group_policies("G1")} == {"E1", "E2"}


def test_forty_vehicles_moved_from_p205_to_p101(store):
    transfers = store.transfers(date(2025, 12, 31), date(2026, 6, 30))
    assert len(transfers) == 40
    assert {t["from_policy"] for t in transfers} == {"P205"}
    assert {t["to_policy"] for t in transfers} == {"P101"}
    assert all(t["effective"] == date(2026, 4, 1) for t in transfers)
    assert "V041" in {t["vehicle_id"] for t in transfers}


def test_p205_has_sixty_vehicles_at_renewal_including_v041_removed(store):
    vehicles = {v["vehicle_id"] for v in store.vehicles_on_policy("P205", AS_OF)}
    assert len(vehicles) == 60
    assert "V041" not in vehicles
    assert "V001" in vehicles


def test_vehicle_history_is_time_valid(store):
    history = store.vehicle_history("V041")
    assert [(h["policy_id"], h["valid_from"]) for h in history] == [
        ("P205", date(2025, 4, 1)),
        ("P101", date(2026, 4, 1)),
    ]
    assert store.assignment_on("V041", date(2025, 9, 1))["policy_id"] == "P205"
    assert store.assignment_on("V041", date(2026, 9, 1))["policy_id"] == "P101"


# --- the three governed metrics ------------------------------------------
def test_deck_metrics_reproduce(store, registry):
    v1 = policy_metrics(store, registry, "P205", AS_OF, "v1")
    v2 = policy_metrics(store, registry, "P205", AS_OF, "v2")

    assert v1["loss_ratio"] == pytest.approx(0.50, abs=1e-4)   # incurred / premium
    assert v2["loss_ratio"] == pytest.approx(0.60, abs=1e-4)   # + ALAE, the v2 definition
    assert v1["frequency"] == pytest.approx(13.33, abs=0.01)   # per 100 vehicle-years
    assert v1["severity"] == pytest.approx(30000, abs=1)       # per claim
    assert v1["vehicle_years"] == pytest.approx(45.01, abs=0.05)


def test_metric_versions_are_declared_and_lineaged(registry):
    assert registry.versions["loss_ratio"] == ["v1", "v2"]
    assert registry.current("loss_ratio") == "v2"
    spec = registry.spec("loss_ratio", "v2")
    assert "alae" in spec["formula"]
    assert spec["supersedes"] == "v1"


def test_prior_claim_does_not_enter_the_current_period(store, registry):
    # CL001 sits on V041 in Aug 2025 — outside P205's current period
    metrics = policy_metrics(store, registry, "P205", AS_OF, "v2")
    assert metrics["claim_count"] == 6
    assert metrics["incurred"] == 180000


# --- rules and decision ---------------------------------------------------
def test_both_rules_fire_and_the_recommendation_matches_the_deck(store, registry):
    result = assess_policy(store, registry, "P205", AS_OF, "v2")
    fired = {f["rule_id"] for f in result["findings"] if f["breached"]}
    assert fired == {"FR1_LOSS_RATIO", "FR2_GROUP_SCALE"}
    assert result["decision"] == "Refer for senior review + group assessment"
    assert "Underwriter retains the final decision" in result["underwriter_note"]


def test_evidence_carries_v041_history_without_triggering(store, registry):
    # on P205 the fleet left, so V041 shows up as a transfer-out with a prior claim
    p205 = assess_policy(store, registry, "P205", AS_OF, "v2")
    kinds = {e["kind"] for e in p205["evidence"]}
    assert {"prior_claim", "transferred_out"} <= kinds
    v041 = [e for e in p205["evidence"] if e.get("vehicle_id") == "V041"]
    assert v041 and any(e["kind"] == "prior_claim" and e["incurred"] == 500000 for e in v041)

    # transfers are summarised, not one row per vehicle
    transfer = next(e for e in p205["evidence"] if e["kind"] == "transferred_out")
    assert transfer["count"] == 40 and transfer["other_policy"] == "P101"
    assert "V041" in transfer["vehicle_id"]

    # on P101 the same vehicles arrive, and their history arrives with them
    p101 = assess_policy(store, registry, "P101", AS_OF, "v2")
    arrival = next(e for e in p101["evidence"] if e["kind"] == "transferred_in")
    assert arrival["count"] == 40 and "V041" in arrival["vehicle_id"]

    # evidence never changes the decision on its own
    assert all("breached" not in e for e in p205["evidence"])


def test_group_aggregation_is_the_only_place_120_is_exceeded(store, registry):
    p205 = assess_policy(store, registry, "P205", AS_OF, "v2")
    assert p205["metrics"]["vehicles"] == 60
    assert p205["group_metrics"]["vehicles"] == 150
    assert p205["findings"][1]["actual"] == 150


# --- lifecycle / impact trace --------------------------------------------
def test_impact_trace_shows_which_decisions_move(store, registry):
    trace = impact_trace(store, registry, AS_OF)
    assert trace["total"] == 2
    assert trace["changed"] == 2
    for row in trace["policies"]:
        assert row["loss_ratio_before"] < 0.60 <= row["loss_ratio_after"]
        assert row["decision_before"] != row["decision_after"]


def test_assessment_is_reproducible(store, registry):
    first = assess_policy(store, registry, "P205", AS_OF, "v2")
    second = assess_policy(store, registry, "P205", AS_OF, "v2")
    assert first["decision"] == second["decision"]
    assert first["metrics"] == second["metrics"]
    assert first["evidence"] == second["evidence"]


def test_unknown_policy_is_none(store, registry):
    assert assess_policy(store, registry, "P999", AS_OF, "v2") is None


def test_group_metrics_reconcile_with_policy_metrics(store, registry):
    group = group_metrics(store, registry, "G1", AS_OF, "v2")
    policies = [policy_metrics(store, registry, p["policy_id"], AS_OF, "v2")
                for p in store.group_policies("G1")]
    assert group["premium"] == pytest.approx(sum(p["premium"] for p in policies))
    assert group["claim_count"] == sum(p["claim_count"] for p in policies)


# --- API surface ----------------------------------------------------------
def test_fleet_endpoints_expose_the_same_numbers():
    from fastapi.testclient import TestClient

    from iaa.api import app

    client = TestClient(app)
    body = client.get("/fleet/policies/P205/assessment", params={"as_of": "2026-12-31"}).json()
    assert body["metrics"]["loss_ratio"] == pytest.approx(0.60, abs=1e-4)
    assert body["decision"] == "Refer for senior review + group assessment"

    listing = client.get("/fleet/policies").json()
    assert listing["metrics_version"] == "v2"
    assert {p["policy_id"] for p in listing["policies"]} == {"P101", "P205"}

    trace = client.get("/fleet/impact-trace", params={"as_of": "2026-12-31"}).json()
    assert trace["changed"] == 2

    assert client.get("/fleet/policies/NOPE/assessment").status_code == 404
    assert client.get("/fleet/groups/G1").json()["metrics"]["vehicles"] == 150
