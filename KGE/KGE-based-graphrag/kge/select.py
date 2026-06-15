from __future__ import annotations

import sys

from kge.paths import PROJECT_ROOT
from kge.retrieve import (
    _load_kge_link_arrays,
    _load_triple_rows,
    kge_link_prediction_ready,
    trans_e_score,
)

# Reuse GraphRAG's shared output-contract modules (later tasks).
sys.path.insert(0, str(PROJECT_ROOT / "GraphRag"))


def transe_expand(seed_uris: list[str], *, top_k: int = 8) -> list[str]:
    """Expand seeds to related entities by ranking the REAL triples that contain
    a seed (TransE plausibility -‖h+r−t‖). Returns entities from those real
    triples only — never fabricates a triple or an entity."""
    if not seed_uris or not kge_link_prediction_ready():
        return []
    entity_ids, relation_ids, entity_kge, relation_kge = _load_kge_link_arrays()
    eidx = {u: i for i, u in enumerate(entity_ids)}
    ridx = {u: i for i, u in enumerate(relation_ids)}
    seeds = set(seed_uris)
    scored: list[tuple[float, str, str]] = []
    for h, r, t in _load_triple_rows():
        if (h in seeds or t in seeds) and h in eidx and r in ridx and t in eidx:
            s = trans_e_score(entity_kge[eidx[h]], relation_kge[ridx[r]], entity_kge[eidx[t]])
            scored.append((s, h, t))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    out: list[str] = []
    for _s, h, t in scored[:top_k]:
        for e in (h, t):
            if e not in seeds and e not in out:
                out.append(e)
    return out


from rdflib import URIRef  # noqa: E402

from ontology_graph import load_ontology  # noqa: E402
from resource_index import build_resource_index, to_curie  # noqa: E402
from graph_relations import (  # noqa: E402
    traverse_connective,
    closed_vocab_for_reached_roles,
)
from context_builder import serialize_context  # noqa: E402
from kge.paths import ONTOLOGY_DIR  # noqa: E402

_GRAPH = None
_RESOURCES = None


def _ontology():
    """Load + index the ontology once (cached); avoids re-parsing per case."""
    global _GRAPH, _RESOURCES
    if _GRAPH is None:
        _GRAPH = load_ontology(ONTOLOGY_DIR)
        _RESOURCES = build_resource_index(_GRAPH)
    return _GRAPH, _RESOURCES


def assemble_context(grounded_uris: list[str]) -> str:
    """Turn an embedding-selected grounded URI set into the SHARED GraphRAG
    output contract (@prefix + grounded terms + connective relations + closed
    vocab). Mirrors GraphRag.subgraph_retriever.build_retrieval_context, but the
    seeds come from KGE selection rather than lexical/deterministic grounding."""
    graph, resources = _ontology()
    by_uri = {r.uri: r for r in resources}
    seen: list[str] = []
    for u in grounded_uris:
        if u not in seen:
            seen.append(u)
    grounded_uris = seen

    relations_raw, reached = traverse_connective(graph, [URIRef(u) for u in grounded_uris])
    for u in grounded_uris:
        r = by_uri.get(u)
        if r and r.role_class:
            reached.add(r.role_class)

    relations = [
        (to_curie(str(s)), to_curie(str(p)), to_curie(str(o)))
        for s, p, o in relations_raw
    ]
    grounded = [
        (
            (by_uri[u].labels[0] if by_uri[u].labels else by_uri[u].curie),
            by_uri[u].curie,
            "; ".join(by_uri[u].rdf_types) or "resource",
            by_uri[u].comment[:160],
        )
        for u in grounded_uris
        if u in by_uri and by_uri[u].role_class is not None
    ]
    vocab = closed_vocab_for_reached_roles(reached, resources)
    return serialize_context(grounded, relations, vocab)


import json  # noqa: E402
import os  # noqa: E402

import numpy as np  # noqa: E402

from kge.retrieve import _load_arrays, _embed_query, kge_ready  # noqa: E402
from kge.paths import MANIFEST_JSON  # noqa: E402

TEXT_TOP_K = 8
EXPAND_TOP_K = 8


def _resolve_embedding_model() -> str:
    if MANIFEST_JSON.is_file():
        m = json.loads(MANIFEST_JSON.read_text(encoding="utf-8")).get("text_embedding_model")
        if m:
            return m
    return "text-embedding-3-small"


def text_ground(query: str, *, top_k: int = TEXT_TOP_K, case_id: str | None = None) -> list[str]:
    """Dense entity retrieval: cosine(query text embedding, entity text
    embeddings) -> top-k entity URIs. Catches non-lexical / synonym mentions."""
    if not kge_ready():
        return []
    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    entity_ids, _kge, text_emb = _load_arrays()
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prev = os.getenv("KGE_ACTIVE_CASE_ID")
    if case_id:
        os.environ["KGE_ACTIVE_CASE_ID"] = case_id
    try:
        q = _embed_query(client, query, _resolve_embedding_model())
    finally:
        if case_id:
            if prev is None:
                os.environ.pop("KGE_ACTIVE_CASE_ID", None)
            else:
                os.environ["KGE_ACTIVE_CASE_ID"] = prev
    scores = text_emb @ q
    idx = np.argsort(-scores)[:top_k]
    return [entity_ids[i] for i in idx.tolist()]


def build_kge_context(query: str, *, case_id: str | None = None) -> str:
    """Canonical KGE retrieval context: text-embedding grounding + TransE
    real-triple expansion -> shared GraphRAG output contract."""
    seeds = text_ground(query, case_id=case_id)
    expanded = transe_expand(seeds, top_k=EXPAND_TOP_K)
    return assemble_context(seeds + expanded)
