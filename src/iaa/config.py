"""Runtime configuration for the Insurance Ontology Accelerator POC."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.getenv("IAA_DATA_DIR", ROOT / "data"))
ONTOLOGY_PATH = Path(os.getenv("IAA_ONTOLOGY", ROOT / "ontology" / "insurance_ontology.yaml"))

# Claims are scored against a rolling 36 month window ending "today".
AS_OF_DATE = os.getenv("IAA_AS_OF", "")  # blank -> real today


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str = os.getenv("NEO4J_URI", "")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "")
    database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    @property
    def configured(self) -> bool:
        return bool(self.uri)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = DATA_DIR
    ontology_path: Path = ONTOLOGY_PATH
    neo4j: Neo4jSettings = field(default_factory=Neo4jSettings)
    claims_window_months: int = 36
    as_of: str = AS_OF_DATE


settings = Settings()
