"""Source-to-canonical mapping and validation behave as the ontology says."""

from __future__ import annotations

from pathlib import Path

from iaa.ingest import map_source_file, validate_entity
from iaa.ontology import get_ontology

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "source" / "property_schedule_raw.csv"


def test_raw_schedule_maps_to_canonical_property():
    rows, issues = map_source_file(RAW)
    assert len(rows) == 8
    assert [i for i in issues if i.severity == "error"] == []

    first = rows[0]
    assert first["property_id"] == "PR001"
    assert first["construction_type"] == "Masonry"
    assert first["occupancy"] == "Office"
    assert first["sprinklered"] is True
    assert first["flood_zone"] == "X"
    assert first["state"] == "NH"
    assert first["policy_id"] == "P1001"
    assert 4199 < first["gross_floor_area_sqm"] < 4201  # 45,208 sqft -> 4,200 sqm
    assert first["year_built"] == 1998


def test_code_translation_covers_frame_and_steel():
    rows, _ = map_source_file(RAW)
    by_id = {r["property_id"]: r for r in rows}
    assert by_id["PR002"]["construction_type"] == "Frame"
    assert by_id["PR003"]["construction_type"] == "Steel"
    assert by_id["PR002"]["sprinklered"] is False
    assert by_id["PR002"]["flood_zone"] == "AE"
    assert by_id["PR008"]["occupancy"] == "Hotel"


def test_missing_required_field_is_rejected():
    ontology = get_ontology()
    rows = [
        {"property_id": "PR900", "policy_id": "P1001", "address": "1 Test St", "construction_type": "Steel",
         "year_built": "2001", "occupancy": "Office", "sum_insured": "1000", "sprinklered": "true", "flood_zone": "X"},
        {"property_id": "PR901", "policy_id": "P1001", "address": "", "construction_type": "Steel",
         "year_built": "2001", "occupancy": "Office", "sum_insured": "1000", "sprinklered": "true", "flood_zone": "X"},
    ]
    clean, issues = validate_entity(ontology, "Property", rows)
    assert [r["property_id"] for r in clean] == ["PR900"]
    assert any(i.key == "PR901" and i.attribute == "address" for i in issues)


def test_ontology_defines_the_six_poc_entities():
    onto = get_ontology()
    assert set(onto.entities) == {"Customer", "Policy", "Property", "Coverage", "Claim", "RiskAssessment"}
    names = {r.name for r in onto.relationships}
    assert {"BUYS", "COVERS", "HAS_COVERAGE", "HAS_CLAIM", "CLAIMED_ON", "HAS_RISK"} <= names
    assert onto.entity("Property").key == "property_id"
    assert "property_id" in onto.entity("Property").required_attributes
