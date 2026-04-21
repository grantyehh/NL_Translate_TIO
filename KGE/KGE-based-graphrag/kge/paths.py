"""Paths and filenames for KGE artifacts (relative to the shared CHT root)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
KGE_DATA_DIR = EXPERIMENT_ROOT / "kge_data"
ONTOLOGY_DIR = PROJECT_ROOT / "TM Forum Intent Ontology"

TRIPLES_TSV = KGE_DATA_DIR / "triples.tsv"
ENTITY_IDS_JSON = KGE_DATA_DIR / "entity_ids.json"
ENTITY_KGE_EMB_NPY = KGE_DATA_DIR / "entity_kge_embeddings.npy"
ENTITY_TEXT_EMB_NPY = KGE_DATA_DIR / "entity_text_embeddings.npy"
MANIFEST_JSON = KGE_DATA_DIR / "manifest.json"
