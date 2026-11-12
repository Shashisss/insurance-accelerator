"""Claims reserving: two valuations, one decomposed movement."""

from __future__ import annotations

import pytest

from iaa.reserving import assess, load_book, position, top_movements

CR = 1e7


@pytest.fixture(scope="module")
def book():
    return load_book()


@pytest.fixture(scope="module")
def result(book):
    return assess(book)


def test_two_valuations_with_the_decks_numbers(result):
    assert result["baseline"]["ultimate"] == pytest.approx(20.0 * CR, rel=1e-6)
    assert result["revised"]["ultimate"] == pytest.approx(23.0 * CR, rel=1e-6)
    assert result["change_pct"] == pytest.approx(0.15, abs=1e-4)
    assert result["alert"] is True


def test_drivers_reconcile_exactly(result):
    total = sum(d["impact"] for d in result["drivers"])
    assert total == pytest.approx(result["change"], abs=1.0)
    assert result["reconciled"] == pytest.approx(0.0, abs=1.0)
    names = {d["driver"] for d in result["drivers"]}
    assert names == {"Incurred movement", "Selection change", "Maturity"}


def test_decision_is_actuarial_review(result):
    assert "actuarial review" in result["decision"].lower()
    assert result["threshold"] == pytest.approx(0.10)


def test_position_components_add_up(book):
    pos = position(book, "2027-03")
    assert pos["incurred"] == pytest.approx(pos["paid"] + pos["case"], abs=1.0)
    assert pos["ultimate"] == pytest.approx(sum(s["ultimate"] for s in pos["by_segment"]), abs=1.0)
    assert pos["ibnr"] == pytest.approx(pos["ultimate"] - pos["incurred"], abs=1.0)
    assert pos["claims"] == 60


def test_baseline_and_revised_differ_in_the_expected_direction(book):
    base = position(book, "2026-12")
    rev = position(book, "2027-03")
    assert rev["ultimate"] > base["ultimate"]
    assert rev["paid"] > base["paid"]           # claims paid out over the quarter
    assert rev["factor_version"] != base["factor_version"]


def test_largest_movements_are_third_party_injury(book):
    rows = top_movements(book, limit=5)
    assert all(r["change"] > 0 for r in rows)
    assert any(r["segment"] == "Third party injury" for r in rows)
    assert rows == sorted(rows, key=lambda r: r["change"], reverse=True)
