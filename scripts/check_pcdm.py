"""Check our six entities against the OMG P&C Data Model.

    python scripts/check_pcdm.py

The `pcdm` package ships the model as SQLAlchemy tables. If it is installed, we
verify that every table we claim to align to actually exists, and every column
we map to is really there. If it is not installed, the check reports what it
would have verified — it never silently passes.

Exit code 1 on any mismatch, so it can sit in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_alignment() -> dict:
    return yaml.safe_load((ROOT / "ontology" / "pcdm_alignment.yaml").read_text(encoding="utf-8"))


def pcdm_metadata():
    """Return the SQLAlchemy metadata of the OMG P&C model, or None."""
    try:
        import importlib
        import pkgutil

        import pcdm  # type: ignore
        from pcdm.base import Base  # type: ignore
    except Exception:
        return None

    for module in pkgutil.iter_modules(pcdm.__path__):
        try:
            importlib.import_module(f"pcdm.{module.name}")
        except Exception:
            continue
    return Base.metadata


def main() -> int:
    spec = load_alignment()
    meta = pcdm_metadata()
    failures = 0

    print(f"standard: {spec['standard']['name']}  ({spec['standard']['licence']})")
    print(f"pcdm package installed: {'yes' if meta is not None else 'no — names not verified'}\n")
    print(f"{'our entity':16} {'pcdm table':18} {'status':10} notes")
    print("-" * 78)

    for name, row in spec["entities"].items():
        table = row.get("pcdm_table")
        if table is None:
            print(f"{name:16} {'(derived)':18} {'skip':10} {row.get('note', '')[:40]}")
            continue

        if meta is None:
            print(f"{name:16} {table:18} {'unverified':10} install pcdm to check")
            continue

        tbl = meta.tables.get(table)
        if tbl is None:
            print(f"{name:16} {table:18} {'MISSING':10} table not in the OMG model")
            failures += 1
            continue

        bad = []
        for ours, theirs in (row.get("attributes") or {}).items():
            if theirs not in tbl.columns:
                bad.append(f"{ours}->{theirs}")

        status = "ok" if not bad else "BAD COLUMN"
        print(f"{name:16} {table:18} {status:10} " +
              (f"{len(row.get('attributes') or {})} attributes mapped" if not bad else ", ".join(bad)))
        failures += bool(bad)

    print()
    if meta is None:
        print("Not verified: install with `pip install pcdm` to check names against the standard.")
        return 0

    total_tables = len(meta.tables)
    print(f"OMG P&C model in this package: {total_tables} tables. We use "
          f"{sum(1 for r in spec['entities'].values() if r.get('pcdm_table'))} of them.")
    print("PASS" if failures == 0 else f"FAIL — {failures} mismatch(es)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
