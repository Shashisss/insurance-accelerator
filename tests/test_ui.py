"""The workbench renders, and all three use cases live in one app."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "streamlit_app.py")


def _open(use_case: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=150).run()
    if use_case:
        at.radio(key="usecase").set_value(use_case).run()
    return at


def test_app_opens_on_the_fleet_decision():
    at = _open()
    assert not at.exception, [e.value for e in at.exception]
    labels = [m.label for m in at.metric]
    assert "Group fleet" in labels and "Loss ratio" in labels
    assert at.radio(key="usecase").value == "Fleet renewal"


def test_every_use_case_is_reachable_from_the_sidebar():
    at = _open()
    assert list(at.radio(key="usecase").options) == ["Fleet renewal", "Claims reserving", "Pricing adequacy"]


@pytest.mark.parametrize("use_case,expected", [
    ("Fleet renewal", "Group fleet"),
    ("Claims reserving", "Ultimate, baseline"),
    ("Pricing adequacy", "Indicated premium"),
])
def test_each_use_case_renders_its_own_numbers(use_case, expected):
    at = _open(use_case)
    assert not at.exception, [e.value for e in at.exception]
    assert expected in [m.label for m in at.metric]


def test_ask_panel_answers_on_every_use_case():
    for use_case, question in [
        ("Fleet renewal", "Why is P205 referred?"),
        ("Claims reserving", "Did reserves develop adversely?"),
        ("Pricing adequacy", "What is the indicated premium?"),
    ]:
        at = _open(use_case)
        prefix = {"Fleet renewal": "fleet", "Claims reserving": "claims", "Pricing adequacy": "pricing"}[use_case]
        at.button(key=f"{prefix}::sugg::{question}").click().run()
        assert not at.exception, use_case
        assert at.success, f"{use_case}: the ask panel must return an answer"


def test_claims_screen_flags_the_adverse_movement():
    at = _open("Claims reserving")
    assert any("actuarial review" in e.value.lower() for e in at.error)


def test_pricing_screen_matches_the_framework_numbers():
    at = _open("Pricing adequacy")
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Indicated premium"] == "₹12.79L"


def test_property_workbench_still_runs():
    at = AppTest.from_file(str(ROOT / "property_app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Risk score" in [m.label for m in at.metric]
    assert any(b.label == "Property" and b.value.startswith("PR001") for b in at.selectbox)
