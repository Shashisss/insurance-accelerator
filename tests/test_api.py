"""The API exposes the same assessment the rules engine produces."""

from __future__ import annotations

from fastapi.testclient import TestClient

from iaa.api import app

client = TestClient(app)


def test_health_reports_backend_and_versions():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["graph"]["ok"] is True
    assert body["graph"]["counts"]["Property"] == 12
    assert body["ruleset_version"]


def test_property_list_includes_scores():
    body = client.get("/properties").json()
    assert body["count"] == 12
    row = next(p for p in body["properties"] if p["property_id"] == "PR001")
    assert row["band"] in {"Low", "Medium", "High", "Decline"}
    assert row["score"] is not None


def test_assessment_endpoint_explains_the_score():
    body = client.get("/properties/PR005/assessment", params={"as_of": "2026-11-03"}).json()
    assert body["property_id"] == "PR005"
    assert body["band"] == "Decline"
    assert body["hard_stops"]
    assert any(f["points"] > 0 for f in body["findings"])
    assert body["context"]["claims"]


def test_unknown_property_is_404():
    assert client.get("/properties/NOPE/assessment").status_code == 404


def test_ontology_endpoint_matches_model():
    body = client.get("/ontology").json()
    assert set(body["entities"]) == {"Customer", "Policy", "Property", "Coverage", "Claim", "RiskAssessment"}
    assert body["thresholds"]["high"] == 45
