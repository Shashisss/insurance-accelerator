"""The rules must be visible in the app and checkable against the engine."""

from __future__ import annotations

from iaa.graph import EmbeddedStore
from iaa.ingest import load_canonical
from iaa.ontology import get_ontology
from iaa.risk import assess_all, assess_property
from iaa.validation import audit_assessment


def test_every_rule_is_described_for_the_ui():
    catalogue = get_ontology().rule_catalogue()
    assert len(catalogue) == 8
    for row in catalogue:
        assert row["id"].startswith("R")
        assert row["name"]
        assert row["points"], f"{row['id']} has no readable scoring table"
        assert row["rationale"], f"{row['id']} has no rationale"
        assert row["max_points"] >= 0


def test_points_text_reads_like_a_table():
    by_id = {row["id"]: row for row in get_ontology().rule_catalogue()}

    assert by_id["R01_CONSTRUCTION"]["points"].startswith("Frame 18")
    assert "Masonry 6" in by_id["R01_CONSTRUCTION"]["points"]

    age = by_id["R02_BUILDING_AGE"]["points"]
    assert "≤15y 0" in age and "≤70y 10" in age and "> 70y 16" in age

    assert "V 22" in by_id["R03_FLOOD_ZONE"]["points"]
    assert "no sprinklers 10" in by_id["R04_SPRINKLER"]["points"]
    assert "Restaurant 12" in by_id["R05_OCCUPANCY"]["points"]

    claims = by_id["R06_CLAIMS_HISTORY"]["points"]
    assert "per claim" in claims and "capped at 25" in claims

    assert "≥95% 0" in by_id["R07_UNDERINSURANCE"]["points"]
    assert "≤4 0" in by_id["R08_PROTECTION_CLASS"]["points"]


def test_scoring_summary_matches_the_yaml():
    summary = get_ontology().scoring_summary()
    assert summary["rule_count"] == 8
    assert summary["hard_stop_count"] == 3
    assert summary["max_score"] == 100
    assert summary["thresholds"] == {"medium": 25, "high": 45, "decline": 65}


def test_engine_and_configuration_agree_for_every_property():
    store = EmbeddedStore(load_canonical())
    ontology = get_ontology()
    for assessment in assess_all(store, as_of="2026-11-03"):
        rows = audit_assessment(ontology, assessment)
        assert len(rows) == 8
        bad = [r for r in rows if not r["matches"]]
        assert not bad, f"{assessment['property_id']}: {bad}"


def test_audit_notices_a_deliberate_mismatch():
    """If the config and the engine disagree, the check must say so."""
    store = EmbeddedStore(load_canonical())
    assessment = assess_property(store, "PR002", as_of="2026-11-03", persist=False)
    finding = next(f for f in assessment["findings"] if f["rule_id"] == "R01_CONSTRUCTION")
    tampered = dict(finding)
    tampered["points"] = 99

    from iaa.validation import audit

    rule = next(item.raw for item in get_ontology().rule_items if item.id == "R01_CONSTRUCTION")
    row = audit(rule, tampered)
    assert row["matches"] is False
    assert row["expected"] == 18
    assert row["applied"] == 99


def test_hard_stops_are_documented():
    stops = get_ontology().hard_stops
    assert {s["id"] for s in stops} == {"HS01_HIGH_FLOOD", "HS02_OLD_FRAME_UNSPRINKLERED", "HS03_LARGE_RECENT_LOSS"}
    for stop in stops:
        assert stop["reason"]
        assert stop["when"]
