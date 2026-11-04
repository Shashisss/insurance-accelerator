"""The graph views and exports are built from the same store the engine uses."""

from __future__ import annotations

from iaa.graph import EmbeddedStore
from iaa.ingest import load_canonical
from iaa.risk import assess_all, assess_property
from iaa.viz import cypher_for_property, dot_for_book, dot_for_property


def test_property_dot_contains_the_360_view():
    store = EmbeddedStore(load_canonical())
    assessment = assess_property(store, "PR005", as_of="2026-11-03", persist=False)
    dot = dot_for_property(store, "PR005", assessment)

    assert dot.startswith("digraph property {")
    assert dot.rstrip().endswith("}")
    # every entity type in the path is drawn
    for marker in ("C:C005", "P:P1005", "PR:PR005", "CV:CV010", "CL:CL005", "RA:"):
        assert marker in dot
    # relationships are labelled with the ontology's edge names
    for rel in ("BUYS", "COVERS", "HAS_COVERAGE", "HAS_CLAIM", "HAS_RISK"):
        assert rel in dot
    assert "Decline" in dot


def test_property_dot_quotes_are_balanced():
    store = EmbeddedStore(load_canonical())
    dot = dot_for_property(store, "PR001")
    assert dot.count('"') % 2 == 0
    assert dot.count("{") == dot.count("}")


def test_book_dot_covers_every_property():
    store = EmbeddedStore(load_canonical())
    dot = dot_for_book(store, assess_all(store, as_of="2026-11-03"))
    for prop in store.list_properties():
        assert f'PR:{prop["property_id"]}' in dot
    assert dot.count("PR:") >= 12


def test_cypher_export_is_pasteable():
    store = EmbeddedStore(load_canonical())
    cypher = cypher_for_property(store, "PR002")
    assert "CREATE (:Property" in cypher
    assert "MATCH (p:Policy" in cypher
    assert cypher.count(";") == len([line for line in cypher.splitlines() if line.strip()])
    assert "'SHINGLE'" not in cypher  # already mapped to canonical values
    assert "Frame" in cypher


def test_unknown_property_returns_none():
    store = EmbeddedStore(load_canonical())
    assert dot_for_property(store, "NOPE") is None
    assert cypher_for_property(store, "NOPE") is None
