"""Canonical model, loaded from the ontology YAML.

Everything downstream (mapping, graph load, rules, API, UI) reads this module so
that there is exactly one definition of an entity or an attribute in the POC.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Attribute:
    name: str
    type: str
    required: bool
    definition: str


@dataclass(frozen=True)
class Entity:
    name: str
    key: str
    definition: str
    attributes: tuple[Attribute, ...]

    def attribute(self, name: str) -> Attribute | None:
        return next((a for a in self.attributes if a.name == name), None)

    @property
    def required_attributes(self) -> tuple[str, ...]:
        return tuple(a.name for a in self.attributes if a.required)


@dataclass(frozen=True)
class Relationship:
    name: str
    source: str
    target: str
    cardinality: str
    definition: str


@dataclass(frozen=True)
class RuleItem:
    id: str
    name: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class Ontology:
    version: str
    domain: str
    entities: dict[str, Entity]
    relationships: tuple[Relationship, ...]
    source_mapping: dict[str, Any]
    rules: dict[str, Any]

    # --- convenience -------------------------------------------------
    def entity(self, name: str) -> Entity:
        try:
            return self.entities[name]
        except KeyError as exc:  # pragma: no cover - programming error
            raise KeyError(f"Unknown entity {name!r}; known: {sorted(self.entities)}") from exc

    @property
    def rule_version(self) -> str:
        return str(self.rules.get("version", self.version))

    @property
    def thresholds(self) -> dict[str, float]:
        return dict(self.rules["scoring"]["thresholds"])

    @property
    def rule_items(self) -> list[RuleItem]:
        return [RuleItem(r["id"], r["name"], r) for r in self.rules["items"]]

    @property
    def hard_stops(self) -> list[dict[str, Any]]:
        return list(self.rules.get("hard_stops", []))

    def describe(self) -> dict[str, Any]:
        """Serialisable view used by /ontology and the UI."""
        return {
            "version": self.version,
            "domain": self.domain,
            "rule_version": self.rule_version,
            "entities": {
                name: {
                    "key": e.key,
                    "definition": e.definition,
                    "attributes": [
                        {"name": a.name, "type": a.type, "required": a.required, "definition": a.definition}
                        for a in e.attributes
                    ],
                }
                for name, e in self.entities.items()
            },
            "relationships": [
                {
                    "name": r.name,
                    "from": r.source,
                    "to": r.target,
                    "cardinality": r.cardinality,
                    "definition": r.definition,
                }
                for r in self.relationships
            ],
            "thresholds": self.thresholds,
        }

    def column_map(self, entity: str) -> dict[str, str]:
        """Canonical attribute -> attribute (identity map, for tabular sources)."""
        return {a.name: a.name for a in self.entity(entity).attributes}


def load_ontology(path: Path | str) -> Ontology:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    entities: dict[str, Entity] = {}
    for name, spec in raw["entities"].items():
        attrs = []
        for attr_name, attr_spec in spec["attributes"].items():
            attrs.append(
                Attribute(
                    name=attr_name,
                    type=str(attr_spec.get("type", "string")),
                    required=bool(attr_spec.get("required", False)),
                    definition=str(attr_spec.get("definition", "")),
                )
            )
        entities[name] = Entity(
            name=name,
            key=str(spec["key"]),
            definition=str(spec.get("definition", "")),
            attributes=tuple(attrs),
        )

    relationships = tuple(
        Relationship(
            name=str(r["name"]),
            source=str(r["from"]),
            target=str(r["to"]),
            cardinality=str(r.get("cardinality", "")),
            definition=str(r.get("definition", "")),
        )
        for r in raw.get("relationships", [])
    )

    return Ontology(
        version=str(raw.get("version", "0")),
        domain=str(raw.get("domain", "")),
        entities=entities,
        relationships=relationships,
        source_mapping=dict(raw.get("source_mapping", {})),
        rules=dict(raw.get("rules", {})),
    )


@lru_cache(maxsize=1)
def get_ontology() -> Ontology:
    from .config import settings

    return load_ontology(settings.ontology_path)
