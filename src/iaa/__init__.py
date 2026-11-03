"""Insurance Ontology Accelerator — minimal POC package."""

from .config import settings
from .graph import EmbeddedStore, Neo4jStore, get_store
from .ingest import Dataset, Issue, load_canonical, map_source_file
from .ontology import get_ontology, load_ontology
from .risk import assess_all, assess_property, portfolio_summary

__all__ = [
    "settings",
    "EmbeddedStore",
    "Neo4jStore",
    "get_store",
    "Dataset",
    "Issue",
    "load_canonical",
    "map_source_file",
    "get_ontology",
    "load_ontology",
    "assess_property",
    "assess_all",
    "portfolio_summary",
]
__version__ = "0.1.0"
