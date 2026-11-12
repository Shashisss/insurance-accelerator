"""Both workbenches render without exceptions, and the fleet page is the entry point."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "streamlit_app.py")          # fleet — the deployed entry point
PROPERTY_APP = str(ROOT / "property_app.py")  # property workbench, kept runnable


def test_fleet_page_is_the_entry_point():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [m.label for m in at.metric]
    assert "Group fleet" in labels and "Loss ratio" in labels
    policy_box = next(b for b in at.selectbox if b.label == "Policy")
    assert policy_box.value.startswith("P205")
    tabs = [t.label for t in at.tabs]
    assert "Ask" not in tabs, "the ask panel now sits above the tabs"
    assert tabs[:2] == ["Graph", "Vehicle timeline"]


def test_fleet_page_follows_the_selected_policy():
    at = AppTest.from_file(APP, default_timeout=120).run()
    policy_box = next(b for b in at.selectbox if b.label == "Policy")
    policy_box.set_value("P101 · Commercial Vehicle Fleet · renews 2027-01-01").run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["P205 fleet at renewal"] == "90"  # P101 covers 90 vehicles


def test_assistant_answers_on_the_page():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.button(key="sugg::Why is P205 referred?").click().run()
    assert not at.exception
    assert any("Refer for senior review" in s.value for s in at.success)


def test_property_workbench_still_runs():
    at = AppTest.from_file(PROPERTY_APP, default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [m.label for m in at.metric]
    assert "Risk score" in labels
    assert any(b.label == "Property" and b.value.startswith("PR001") for b in at.selectbox)


import pytest

PAGES = {
    "claims": str(ROOT / "pages" / "2_Claims_reserving.py"),
    "pricing": str(ROOT / "pages" / "3_Pricing_adequacy.py"),
}


@pytest.mark.parametrize("page", list(PAGES))
def test_use_case_pages_render(page):
    at = AppTest.from_file(PAGES[page], default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.metric, "each page must lead with its numbers"


def test_claims_page_shows_the_adverse_alert():
    at = AppTest.from_file(PAGES["claims"], default_timeout=120).run()
    assert any("actuarial review" in e.value.lower() for e in at.error)


def test_pricing_page_matches_the_deck():
    at = AppTest.from_file(PAGES["pricing"], default_timeout=120).run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Indicated premium"] == "₹12.79L"
