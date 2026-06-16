from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rdflib import Graph, URIRef

from resource_index import OntologyResource, to_curie
from graph_relations import (
    traverse_connective,
    closed_vocab_for_reached_roles,
    extract_conventions,
)
from context_builder import serialize_context

LEXICAL_WEIGHT = 0.45
VECTOR_WEIGHT = 0.55
VECTOR_CUTOFF = 0.20


@dataclass(frozen=True)
class ResourceMatch:
    curie: str
    uri: str
    score: float


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _aliases(r: OntologyResource) -> set[str]:
    out = {_norm(x) for x in (*r.labels, *r.alt_labels)}
    out.add(_norm(r.curie.split(":")[-1]))
    return {a for a in out if a}


def _lexical(query: str, r: OntologyResource) -> float:
    q = _norm(query)
    qtok = set(q.split())
    best = 0.0
    for alias in _aliases(r):
        if alias == q or alias in qtok or (len(alias) > 2 and alias in q):
            return 1.0
        atok = set(alias.split())
        if atok and atok <= qtok:
            best = max(best, 0.8)
        if atok:
            inter = len(atok & qtok)
            if inter:
                best = max(best, 0.6 * inter / len(atok | qtok))
    return best


def ground_query(
    query: str,
    resources: list[OntologyResource],
    embeddings: np.ndarray | None,
    query_vector: np.ndarray | None,
    top_k: int = 12,
) -> list[ResourceMatch]:
    vec_scores = np.zeros(len(resources), dtype=np.float32)
    if embeddings is not None and query_vector is not None:
        qn = float(np.linalg.norm(query_vector))
        if qn > 0:
            rn = np.linalg.norm(embeddings, axis=1)
            ok = rn > 0
            vec_scores[ok] = (embeddings[ok] @ (query_vector / qn)) / rn[ok]
    scored: list[ResourceMatch] = []
    for i, r in enumerate(resources):
        lex = _lexical(query, r)
        vec = float(vec_scores[i]) if vec_scores[i] >= VECTOR_CUTOFF else 0.0
        combined = LEXICAL_WEIGHT * lex + VECTOR_WEIGHT * vec
        if combined > 0:
            scored.append(ResourceMatch(curie=r.curie, uri=r.uri, score=combined))
    scored.sort(key=lambda m: (-m.score, m.curie))
    return scored[:top_k]


def build_retrieval_context(
    query: str,
    graph: Graph,
    resources: list[OntologyResource],
    embeddings: np.ndarray | None,
    query_vector: np.ndarray | None,
) -> str:
    by_curie = {r.curie: r for r in resources}
    matches = ground_query(query, resources, embeddings, query_vector)
    grounded_uris = [URIRef(m.uri) for m in matches]
    relations_raw, reached = traverse_connective(graph, grounded_uris)
    for m in matches:
        rc = by_curie[m.curie].role_class
        if rc:
            reached.add(rc)
    relations = [
        (to_curie(str(s)), to_curie(str(p)), to_curie(str(o)))
        for s, p, o in relations_raw
    ]
    grounded = [
        (
            by_curie[m.curie].labels[0] if by_curie[m.curie].labels else m.curie,
            m.curie,
            "; ".join(by_curie[m.curie].rdf_types) or "resource",
            by_curie[m.curie].comment[:160],
        )
        for m in matches
        if by_curie[m.curie].role_class is not None
    ]
    vocab = closed_vocab_for_reached_roles(reached, resources)
    conventions = extract_conventions(graph)
    return serialize_context(grounded, relations, vocab, conventions=conventions)
