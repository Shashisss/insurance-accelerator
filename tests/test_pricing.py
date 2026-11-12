"""Pricing: the indication reproduces the deck, and the assumptions matter."""

from __future__ import annotations

import pytest

from iaa.pricing import assess, indication, load_inputs, sensitivity


@pytest.fixture(scope="module")
def spec():
    return load_inputs()


@pytest.fixture(scope="module")
def result(spec):
    return assess(spec)


def test_indication_matches_the_deck(result):
    assert result["current_premium"] == pytest.approx(1_000_000)
    assert result["projected_claims"] == pytest.approx(831_600, rel=1e-6)
    assert result["projected_ratio"] == pytest.approx(0.8316, abs=1e-4)
    assert result["indicated_premium"] == pytest.approx(1_279_385, rel=1e-4)
    assert result["indicated_change"] == pytest.approx(0.2794, abs=1e-4)
    assert result["adequacy_ratio"] == pytest.approx(0.7816, abs=1e-4)


def test_both_rules_breach_and_approval_is_required(result):
    fired = {r["rule_id"] for r in result["rules"] if r["breached"]}
    assert fired == {"PR1_RATE_ADEQUACY", "PR2_CHANGE_APPROVAL"}
    assert result["needs_approval"] is True
    assert "approval" in result["decision"].lower()


def test_sensitivity_brackets_the_indication(spec):
    rows = sensitivity(spec)
    by_name = {r["scenario"]: r for r in rows}
    assert by_name["No trend"]["indicated_premium"] < by_name["Severity only"]["indicated_premium"]
    assert by_name["Severity only"]["indicated_premium"] < by_name["Both trends (indication)"]["indicated_premium"]


def test_trend_assumptions_move_the_price_monotonically(spec):
    low = indication(spec, severity_trend=0.0, frequency_trend=0.0)
    high = indication(spec, severity_trend=0.20, frequency_trend=0.10)
    assert high["indicated_premium"] > low["indicated_premium"]
    assert high["projected_ratio"] > low["projected_ratio"]


def test_target_loss_ratio_scales_the_indication(spec):
    at_65 = indication(spec, target_loss_ratio=0.65)
    at_55 = indication(spec, target_loss_ratio=0.55)
    assert at_55["indicated_premium"] > at_65["indicated_premium"]
    assert at_55["indicated_premium"] == pytest.approx(at_65["indicated_premium"] * 0.65 / 0.55, rel=1e-6)


def test_rate_version_is_carried_through(result):
    assert result["rate_version"] == "R-2027.A"
    assert result["effective_from"] == "2027-01-01"
    assert result["approved_by"]
