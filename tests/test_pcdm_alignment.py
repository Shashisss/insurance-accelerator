"""Our model's alignment to the OMG P&C Data Model stays honest."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = yaml.safe_load((ROOT / "ontology" / "pcdm_alignment.yaml").read_text(encoding="utf-8"))


def test_every_entity_is_accounted_for():
    assert set(SPEC["entities"]) == {
        "Customer", "Policy", "Property", "Coverage", "Claim", "RiskAssessment"
    }


def test_derived_entity_is_labelled_not_faked():
    ra = SPEC["entities"]["RiskAssessment"]
    assert ra["pcdm_table"] is None
    assert ra["confidence"] == "derived"
    assert "no pcdm equivalent" in ra["note"].lower()


def test_standard_is_named_and_licensed():
    assert "Property & Casualty" in SPEC["standard"]["name"]
    assert SPEC["standard"]["licence"]
    assert SPEC["standard"]["implementation"]


def test_divergences_are_declared_with_a_reason():
    topics = {d["topic"].lower() for d in SPEC["divergences"]}
    assert any("time" in t for t in topics)
    assert all(d.get("why") for d in SPEC["divergences"])


def test_mapped_tables_and_columns_exist_in_pcdm():
    pcdm = pytest.importorskip("pcdm", reason="pcdm not installed; names unverified")
    import importlib
    import pkgutil

    from pcdm.base import Base

    for module in pkgutil.iter_modules(pcdm.__path__):
        try:
            importlib.import_module(f"pcdm.{module.name}")
        except Exception:
            continue

    for name, row in SPEC["entities"].items():
        table = row.get("pcdm_table")
        if table is None:
            continue
        assert table in Base.metadata.tables, f"{name}: {table} missing from PCDM"
        columns = Base.metadata.tables[table].columns
        for ours, theirs in (row.get("attributes") or {}).items():
            assert theirs in columns, f"{name}.{ours} -> {table}.{theirs} missing"
