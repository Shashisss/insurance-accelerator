"""The workbench renders without exceptions and shows a score with evidence."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_workbench_renders():
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [m.label for m in at.metric]
    assert "Risk score" in labels and "Decision" in labels
    assert at.selectbox[0].value.startswith("PR001")
    assert len(at.tabs) == 5


def test_workbench_follows_the_selected_property():
    at = AppTest.from_file(APP, default_timeout=90).run()
    at.selectbox[0].set_value("PR005 · 210 Congress St, Portland ME").run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Decision"] == "Decline"
    assert metrics["Band"].endswith("Decline")
