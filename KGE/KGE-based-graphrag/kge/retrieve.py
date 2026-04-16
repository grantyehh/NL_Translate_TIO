"""
Hybrid retrieval: text similarity (OpenAI) + KGE neighborhood expansion (TransE entity space).
Used to augment GraphRAG query context in nl_to_tio.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluate_ttl import TIO_PREFIXES  # noqa: E402
from kge.paths import (  # noqa: E402
    ENTITY_IDS_JSON,
    ENTITY_KGE_EMB_NPY,
    ENTITY_TEXT_EMB_NPY,
    MANIFEST_JSON,
)
from kge.tio_triples import entity_text_description, load_merged_ontology_graph  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

# Retrieval hyperparameters (tuned for ontology size)
TEXT_TOP_SEED = 8
KGE_NEIGHBORS_PER_SEED = 14
MAX_TERMS_IN_PROMPT = 45


def _uri_to_curie(uri: str) -> str:
    for prefix, base in TIO_PREFIXES.items():
        if uri.startswith(base):
            return f"{prefix}:{uri[len(base):]}"
    return uri


def kge_hybrid_ready() -> bool:
    """True when KGE + text embeddings exist for hybrid retrieval."""
    return (
        ENTITY_IDS_JSON.is_file()
        and ENTITY_KGE_EMB_NPY.is_file()
        and ENTITY_TEXT_EMB_NPY.is_file()
    )


def _artifacts_ready() -> bool:
    return kge_hybrid_ready()


def _load_arrays():
    with open(ENTITY_IDS_JSON, "r", encoding="utf-8") as f:
        entity_ids: list[str] = json.load(f)
    kge = np.load(ENTITY_KGE_EMB_NPY)
    text_e = np.load(ENTITY_TEXT_EMB_NPY)
    if len(entity_ids) != kge.shape[0] or len(entity_ids) != text_e.shape[0]:
        raise ValueError("entity_ids length does not match embedding matrices")
    return entity_ids, kge.astype(np.float32), text_e.astype(np.float32)


def _embed_query(client: OpenAI, text: str, model: str) -> np.ndarray:
    resp = client.embeddings.create(model=model, input=text[:8000])
    v = np.asarray(resp.data[0].embedding, dtype=np.float32)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def _top_k_indices(scores: np.ndarray, k: int, exclude: set[int] | None = None) -> list[int]:
    if exclude is None:
        exclude = set()
    # Partial sort
    idx = np.argpartition(-scores, min(k + len(exclude), len(scores) - 1))[: k + len(exclude)]
    idx = idx[np.argsort(-scores[idx])]
    out: list[int] = []
    for i in idx.tolist():
        if i in exclude:
            continue
        out.append(i)
        if len(out) >= k:
            break
    return out


def get_kge_ranked_entities(
    nl_query: str,
    *,
    text_top_seed: int = TEXT_TOP_SEED,
    kge_neighbors_per_seed: int = KGE_NEIGHBORS_PER_SEED,
    max_terms: int = MAX_TERMS_IN_PROMPT,
    embedding_model: str | None = None,
) -> list[tuple[str, str, str]]:
    """
    Return list of (curie, full_iri, reason_tag) for prompt injection.
    reason_tag: 'text' | 'kge_neighbor'
    """
    if not _artifacts_ready():
        return []

    manifest_model = None
    if MANIFEST_JSON.is_file():
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            manifest_model = json.load(f).get("text_embedding_model")

    model = embedding_model or manifest_model or "text-embedding-ada-002"

    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    entity_ids, kge_emb, text_emb = _load_arrays()
    client = OpenAI(api_key=api_key)
    q = _embed_query(client, nl_query, model)

    text_scores = text_emb @ q
    seed_indices = _top_k_indices(text_scores, text_top_seed)

    selected: dict[int, str] = {i: "text" for i in seed_indices}

    # KGE neighborhood expansion from each seed (cosine in entity embedding space)
    for si in seed_indices:
        ref = kge_emb[si]
        sims = kge_emb @ ref
        neigh = _top_k_indices(sims, kge_neighbors_per_seed + 1, exclude={si})
        for ni in neigh:
            if ni not in selected:
                selected[ni] = "kge_neighbor"

    seeds_ordered = sorted(seed_indices, key=lambda x: -text_scores[x])
    seed_set = set(seed_indices)
    kge_only = [i for i in selected if i not in seed_set]
    if kge_only and seed_indices:
        seed_mat = kge_emb[np.array(seed_indices)]
        kge_only_sorted = sorted(
            kge_only,
            key=lambda x: float(np.max(seed_mat @ kge_emb[x])),
            reverse=True,
        )
    elif kge_only:
        kge_only_sorted = sorted(kge_only, key=lambda x: -text_scores[x])
    else:
        kge_only_sorted = []

    ordered = seeds_ordered + kge_only_sorted

    seen: set[int] = set()
    final_order: list[int] = []
    for i in ordered:
        if i not in seen and i < len(entity_ids):
            seen.add(i)
            final_order.append(i)
        if len(final_order) >= max_terms:
            break

    rows: list[tuple[str, str, str]] = []
    for i in final_order:
        uri = entity_ids[i]
        curie = _uri_to_curie(uri)
        tag = selected.get(i, "kge_neighbor")
        rows.append((curie, uri, tag))

    return rows


def format_kge_context_for_prompt(nl_query: str) -> str:
    """
    Human-readable block for LLM: suggested TIO terms from hybrid KGE retrieval.
    Returns empty string if artifacts or API are unavailable.
    """
    try:
        ranked = get_kge_ranked_entities(nl_query)
    except Exception:
        return ""

    if not ranked:
        return ""

    g = load_merged_ontology_graph()
    lines = [
        "### KGE-assisted term hints (TransE + text similarity; prefer official CURIEs below when applicable)",
        "",
    ]
    for curie, uri, tag in ranked:
        short = entity_text_description(g, uri)[:400]
        lines.append(f"- [{tag}] {curie} — {short}")

    return "\n".join(lines) + "\n"
