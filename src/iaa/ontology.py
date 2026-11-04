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


def _fmt_number(value: float | int) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def format_rule_points(raw: dict[str, Any]) -> str:
    """Render a rule's scoring table as one readable line, straight from the YAML."""
    kind = raw.get("kind")

    if kind == "claims":
        per = raw.get("per_claim_points", 0)
        sev = raw.get("severity", {})
        cap = raw.get("max_points")
        parts = [f"{per} per claim in window"]
        if sev:
            parts.append(f"+{sev.get('points', 0)} if total > {_fmt_number(sev.get('total_amount', 0))}")
        if cap:
            parts.append(f"capped at {cap}")
        return " · ".join(parts)

    if kind == "underinsurance":
        bands = sorted(raw.get("ratio_thresholds", []), key=lambda b: float(b["min_ratio"]), reverse=True)
        labels = []
        for index, band in enumerate(bands):
            ratio = float(band["min_ratio"])
            lower = bands[index + 1]["min_ratio"] if index + 1 < len(bands) else None
            if lower in (None, 0, 0.0):
                labels.append(f"<{ratio:.0%} {band['points']}")
            else:
                labels.append(f"≥{ratio:.0%} {band['points']}")
        return " · ".join(labels)

    if "bands" in raw or "banded" in raw:
        bands = sorted(raw.get("bands", []), key=lambda b: b["max"])
        unit = "y" if raw.get("derived") == "age" else ""
        labels, previous = [], None
        for band in bands:
            top = band["max"]
            if previous is None:
                labels.append(f"≤{top}{unit} {band['points']}")
            elif top >= 999:
                labels.append(f"> {previous}{unit} {band['points']}")
            else:
                labels.append(f"≤{top}{unit} {band['points']}")
            previous = top
        return " · ".join(labels)

    points = raw.get("points", {})
    if isinstance(points, dict):
        labels = []
        for key, value in points.items():
            if isinstance(key, bool) or str(key).lower() in {"true", "false"}:
                is_true = key is True or str(key).lower() == "true"
                labels.append(f"{'sprinklered' if is_true else 'no sprinklers'} {value}")
            else:
                labels.append(f"{key} {value}")
        default = raw.get("default_points")
        if default is not None:
            labels.append(f"other/missing {default}")
        return " · ".join(labels)

    return ""


CONDITION_LABELS = {
    "flood_zone": "flood zone",
    "construction_type": "construction type",
    "sprinklered": "sprinklered",
    "year_built_below": "built before",
    "claims_36m_total_above": "claims in 36 months above",
}


def format_condition(when: dict[str, Any]) -> str:
    """Turn a hard-stop condition dict into a sentence a reviewer can read."""
    parts = []
    for key, value in when.items():
        label = CONDITION_LABELS.get(key, key.replace("_", " "))
        if key == "sprinklered":
            parts.append(f"{label} = {'yes' if value else 'no'}")
        elif key == "claims_36m_total_above":
            parts.append(f"{label} {float(value):,.0f}")
        elif key == "year_built_below":
            parts.append(f"{label} {value}")
        elif key == "flood_zone":
            parts.append(f"flood zone {value}")
        elif key == "construction_type":
            parts.append(f"{label} {value}")
        else:
            parts.append(f"{label} {value}")
    return " and ".join(parts)


def describe_rule(raw: dict[str, Any]) -> dict[str, Any]:
    """One row of the rule catalogue: what it reads, what it awards, why."""
    kind = raw.get("kind")
    if kind == "claims":
        reads = "claims in the last 36 months"
        max_points = int(raw.get("max_points", 0))
    elif kind == "underinsurance":
        reads = "sum insured ÷ assessed value"
        max_points = max((int(b["points"]) for b in raw.get("ratio_thresholds", [])), default=0)
    elif "bands" in raw:
        reads = f"{raw.get('derived') or raw.get('attribute')}" + (" (from year built)" if raw.get("derived") == "age" else "")
        max_points = max((int(b["points"]) for b in raw.get("bands", [])), default=0)
    else:
        reads = str(raw.get("attribute", ""))
        max_points = max((int(v) for v in raw.get("points", {}).values()), default=0)

    return {
        "id": raw["id"],
        "name": raw["name"],
        "reads": reads,
        "points": format_rule_points(raw),
        "max_points": max_points,
        "rationale": raw.get("rationale", ""),
        "kind": kind or "attribute",
    }


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

    def rule_catalogue(self) -> list[dict[str, Any]]:
        """Rules, their scoring tables and their rationale — for the UI and /rules."""
        return [describe_rule(item.raw) for item in self.rule_items]

    def scoring_summary(self) -> dict[str, Any]:
        scoring = self.rules.get("scoring", {})
        return {
            "ruleset_version": self.rule_version,
            "max_score": int(scoring.get("max_score", 100)),
            "thresholds": self.thresholds,
            "rule_count": len(self.rule_items),
            "hard_stop_count": len(self.hard_stops),
        }

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
