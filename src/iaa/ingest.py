"""Load source data and map it onto the canonical model.

Two paths in the POC:

* `load_canonical()` reads the clean CSV set (already in canonical shape) and
  validates it against the ontology.
* `map_source_file()` reads the deliberately "dirty" insurer schedule extract
  and maps its columns onto canonical Property attributes using the
  `source_mapping` block in the ontology YAML.

Both return `Dataset` / `(records, issues)` so the loader, the tests and the UI
agree on what "clean" means.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import settings
from .ontology import Ontology, get_ontology

TRUE_VALUES = {"true", "t", "y", "yes", "1"}
FALSE_VALUES = {"false", "f", "n", "no", "0"}

CONSTRUCTION_MAP = {
    "FRM": "Frame",
    "FRAME": "Frame",
    "MSN": "Masonry",
    "MASONRY": "Masonry",
    "STL": "Steel",
    "STEEL": "Steel",
}

OCCUPANCY_MAP = {
    "OFF": "Office",
    "RET": "Retail",
    "WHS": "Warehouse",
    "REST": "Restaurant",
    "MULTI": "Multifamily",
    "LOG": "Logistics",
    "HOTEL": "Hotel",
    "MED": "Medical",
    "MIX": "Mixed-use",
}


@dataclass
class Issue:
    entity: str
    key: str
    attribute: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {
            "entity": self.entity,
            "key": self.key,
            "attribute": self.attribute,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class Dataset:
    customers: dict[str, dict[str, Any]]
    policies: dict[str, dict[str, Any]]
    properties: dict[str, dict[str, Any]]
    coverages: dict[str, dict[str, Any]]
    claims: dict[str, dict[str, Any]]
    issues: list[Issue] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "Customer": len(self.customers),
            "Policy": len(self.policies),
            "Property": len(self.properties),
            "Coverage": len(self.coverages),
            "Claim": len(self.claims),
        }


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------
def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def t_strip(v: Any) -> Any:
    return _clean(v)


def t_strip_upper(v: Any) -> Any:
    return _clean(v).upper()


def t_title_case(v: Any) -> Any:
    s = _clean(v)
    return s.title() if s else ""


def t_to_int(v: Any) -> Any:
    s = _clean(v)
    if s == "":
        return None
    return int(float(s))


def t_to_float(v: Any) -> Any:
    s = re.sub(r"[^0-9.\-]", "", _clean(v))
    return float(s) if s else None


def t_to_bool(v: Any) -> Any:
    s = _clean(v).lower()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return None


def t_sqft_to_sqm(v: Any) -> Any:
    sqft = t_to_float(v)
    return round(sqft * 0.092903, 1) if sqft is not None else None


def t_map_const(v: Any) -> Any:
    s = _clean(v).upper()
    return CONSTRUCTION_MAP.get(s, s.title() if s else None)


def t_map_occupancy(v: Any) -> Any:
    s = _clean(v).upper()
    return OCCUPANCY_MAP.get(s, s.title() if s else None)


TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "strip": t_strip,
    "strip_upper": t_strip_upper,
    "title_case": t_title_case,
    "to_int": t_to_int,
    "to_float": t_to_float,
    "to_bool": t_to_bool,
    "sqft_to_sqm": t_sqft_to_sqm,
    "map_const": t_map_const,
    "map_occupancy": t_map_occupancy,
}


# --------------------------------------------------------------------------
# coercion / validation
# --------------------------------------------------------------------------
def coerce(value: Any, type_name: str) -> Any:
    if value is None or value == "":
        return None
    if type_name == "string":
        return str(value).strip()
    if type_name == "int":
        return int(float(value))
    if type_name == "float":
        return float(value)
    if type_name == "bool":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in TRUE_VALUES:
            return True
        if s in FALSE_VALUES:
            return False
        raise ValueError(f"not a boolean: {value!r}")
    if type_name == "date":
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    return value


def validate_entity(ontology: Ontology, entity: str, records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[Issue]]:
    """Coerce types, enforce required fields, return (clean_records, issues)."""
    spec = ontology.entity(entity)
    clean: list[dict[str, Any]] = []
    issues: list[Issue] = []

    for raw in records:
        row = dict(raw)
        key = _clean(row.get(spec.key, "")) or "<missing-key>"
        ok = True
        for attr in spec.attributes:
            value = row.get(attr.name)
            try:
                row[attr.name] = coerce(value, attr.type)
            except (TypeError, ValueError) as exc:
                issues.append(Issue(entity, key, attr.name, f"cannot read {attr.type}: {exc}"))
                ok = False
                row[attr.name] = None
            if attr.required and row.get(attr.name) in (None, ""):
                issues.append(Issue(entity, key, attr.name, "required value is missing"))
                ok = False
        if ok:
            clean.append(row)
    return clean, issues


def validate_integrity(ontology: Ontology, ds: Dataset) -> list[Issue]:
    issues: list[Issue] = []

    def check(entity: str, key_field: str, rows: Iterable[dict[str, Any]], fk: str, target: dict[str, Any], target_entity: str) -> None:
        for row in rows:
            value = row.get(fk)
            if value and value not in target:
                issues.append(
                    Issue(entity, _clean(row.get(key_field)), fk, f"references unknown {target_entity} {value!r}")
                )

    check("Policy", "policy_id", ds.policies.values(), "customer_id", ds.customers, "Customer")
    check("Property", "property_id", ds.properties.values(), "policy_id", ds.policies, "Policy")
    check("Coverage", "coverage_id", ds.coverages.values(), "policy_id", ds.policies, "Policy")
    check("Claim", "claim_id", ds.claims.values(), "property_id", ds.properties, "Property")
    check("Claim", "claim_id", ds.claims.values(), "policy_id", ds.policies, "Policy")
    return issues


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def load_canonical(data_dir: Path | None = None, ontology: Ontology | None = None) -> Dataset:
    data_dir = Path(data_dir or settings.data_dir)
    ontology = ontology or get_ontology()

    files = {
        "Customer": "customers.csv",
        "Policy": "policies.csv",
        "Property": "properties.csv",
        "Coverage": "coverages.csv",
        "Claim": "claims.csv",
    }
    issues: list[Issue] = []
    loaded: dict[str, dict[str, dict[str, Any]]] = {}

    for entity, filename in files.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing dataset file: {path}")
        rows, row_issues = validate_entity(ontology, entity, _read_csv(path))
        issues.extend(row_issues)
        key = ontology.entity(entity).key
        loaded[entity] = {str(row[key]): row for row in rows}

    ds = Dataset(
        customers=loaded["Customer"],
        policies=loaded["Policy"],
        properties=loaded["Property"],
        coverages=loaded["Coverage"],
        claims=loaded["Claim"],
        issues=issues,
    )
    ds.issues.extend(validate_integrity(ontology, ds))
    return ds


def map_source_file(path: Path | str, entity: str = "Property", ontology: Ontology | None = None) -> tuple[list[dict[str, Any]], list[Issue]]:
    """Apply the ontology's source_mapping to a raw schedule extract."""
    ontology = ontology or get_ontology()
    spec = ontology.source_mapping[entity]
    mapping: dict[str, Any] = spec["fields"]
    raw_rows = _read_csv(Path(path))

    mapped: list[dict[str, Any]] = []
    issues: list[Issue] = []
    target_key = ontology.entity(entity).key

    for idx, raw in enumerate(raw_rows, start=2):  # row 1 is the header
        row: dict[str, Any] = {}
        row_issues: list[Issue] = []
        for source_field, rule in mapping.items():
            target = rule["to"]
            transform = TRANSFORMS[rule["transform"]]
            raw_value = raw.get(source_field)
            try:
                value = transform(raw_value)
            except (TypeError, ValueError) as exc:
                row_issues.append(Issue(entity, f"row{idx}", target, f"{source_field}={raw_value!r}: {exc}"))
                value = None
            row[target] = value
        issues.extend(row_issues)
        mapped.append(row)

    clean, validation_issues = validate_entity(ontology, entity, mapped)
    issues.extend(validation_issues)
    if len(clean) != len(mapped):
        bad = {i.key for i in validation_issues}
        issues.append(Issue(entity, ",".join(sorted(bad)), target_key, f"{len(mapped) - len(clean)} row(s) rejected", "warning"))
    return clean, issues
