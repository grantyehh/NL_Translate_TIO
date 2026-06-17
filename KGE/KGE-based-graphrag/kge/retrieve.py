"""
KGE retrieval: artifact loaders and helpers used by kge/select.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_REPO_ROOT = _PROJECT_ROOT.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kge.paths import (  # noqa: E402
    ENTITY_IDS_JSON,
    ENTITY_KGE_EMB_NPY,
    ENTITY_TEXT_EMB_NPY,
    RELATION_IDS_JSON,
    RELATION_KGE_EMB_NPY,
    TRIPLES_TSV,
)
from kge.tio_triples import entity_text_description, load_merged_ontology_graph  # noqa: F401,E402
from openai_config import load_project_env  # noqa: E402
from token_usage import record_usage  # noqa: E402

load_project_env()

TIO_PREFIXES = {
    "evsla": "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/",
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "mf": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
    "met": "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/",
    "quan": "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/",
    "ig": "http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/",
    "insp": "http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/",
    "pbi": "http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/",
    "pro": "http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/",
}


def _uri_to_curie(uri: str) -> str:
    for prefix, base in TIO_PREFIXES.items():
        if uri.startswith(base):
            return f"{prefix}:{uri[len(base):]}"
    return uri


def kge_ready() -> bool:
    """True when KGE + text embeddings exist for retrieval."""
    return (
        ENTITY_IDS_JSON.is_file()
        and ENTITY_KGE_EMB_NPY.is_file()
        and ENTITY_TEXT_EMB_NPY.is_file()
    )


def kge_link_prediction_ready() -> bool:
    """True when TransE entity and relation artifacts exist."""
    return (
        ENTITY_IDS_JSON.is_file()
        and ENTITY_KGE_EMB_NPY.is_file()
        and RELATION_IDS_JSON.is_file()
        and RELATION_KGE_EMB_NPY.is_file()
    )


def _load_arrays():
    with open(ENTITY_IDS_JSON, "r", encoding="utf-8") as f:
        entity_ids: list[str] = json.load(f)
    kge = np.load(ENTITY_KGE_EMB_NPY)
    text_e = np.load(ENTITY_TEXT_EMB_NPY)
    if len(entity_ids) != kge.shape[0] or len(entity_ids) != text_e.shape[0]:
        raise ValueError("entity_ids length does not match embedding matrices")
    return entity_ids, kge.astype(np.float32), text_e.astype(np.float32)


def _load_kge_link_arrays():
    with open(ENTITY_IDS_JSON, "r", encoding="utf-8") as f:
        entity_ids: list[str] = json.load(f)
    with open(RELATION_IDS_JSON, "r", encoding="utf-8") as f:
        relation_ids: list[str] = json.load(f)
    entity_kge = np.load(ENTITY_KGE_EMB_NPY).astype(np.float32)
    relation_kge = np.load(RELATION_KGE_EMB_NPY).astype(np.float32)
    if len(entity_ids) != entity_kge.shape[0]:
        raise ValueError("entity_ids length does not match entity KGE matrix")
    if len(relation_ids) != relation_kge.shape[0]:
        raise ValueError("relation_ids length does not match relation KGE matrix")
    return entity_ids, relation_ids, entity_kge, relation_kge


def _load_triple_rows() -> list[tuple[str, str, str]]:
    if not TRIPLES_TSV.is_file():
        return []
    rows: list[tuple[str, str, str]] = []
    with open(TRIPLES_TSV, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                rows.append((parts[0], parts[1], parts[2]))
    return rows


def _embed_query(client: OpenAI, text: str, model: str) -> np.ndarray:
    resp = client.embeddings.create(model=model, input=text[:8000])
    case_id = os.getenv("KGE_ACTIVE_CASE_ID")
    usage_path = Path(
        os.getenv(
            "KGE_TOKEN_USAGE_PATH",
            str(_REPO_ROOT / "phase1" / "token_usage" / "token_usage_kge.json"),
        )
    )
    experiment = os.getenv("KGE_TOKEN_USAGE_EXPERIMENT", "kge")
    record_usage(
        usage_path,
        experiment=experiment,
        ledger="online",
        case_id=case_id,
        stage="retrieval_embedding",
        model=model,
        api="embeddings",
        response=resp,
    )
    v = np.asarray(resp.data[0].embedding, dtype=np.float32)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def trans_e_score(head_vec: np.ndarray, relation_vec: np.ndarray, tail_vec: np.ndarray) -> float:
    """Return a TransE score where larger is better."""
    return -float(np.linalg.norm(head_vec + relation_vec - tail_vec, ord=2))
