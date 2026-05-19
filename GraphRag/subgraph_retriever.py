from __future__ import annotations

import json
import math
import re
from typing import Callable

from rdflib import URIRef
from rdflib.term import Node

SEED_PROMPT = """You extract ontology-relevant terms from a network intent.
Output a JSON array of short English terms (1-3 words each), no commentary.
Cover: metric (e.g. latency, packet loss), statistic (p95, p99, average),
scope (hub to all spokes, per spoke, specific spoke), measurement method (TWAMP),
time window (5 minute, hourly, monthly).
Skip tenant names, site names, numbers, and units."""


def _strip_code_fence(text: str) -> str:
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```\s*$", text.strip(), re.DOTALL)
    if fence:
        return fence.group(1)
    return text


def extract_seeds(nl_intent: str, caller: Callable[[str], str]) -> list[str]:
    """Call LLM (via injected caller) to extract a list of ontology seed terms."""
    user_msg = f"{SEED_PROMPT}\n\nIntent: {nl_intent}"
    raw = caller(user_msg)
    raw = _strip_code_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, (str, int, float))]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def ground_seeds(
    seeds: list[str],
    label_index: dict[str, URIRef],
    comment_index: dict[URIRef, str],
    embed_caller: Callable[[list[str]], list[list[float]]],
    similarity_threshold: float = 0.6,
) -> set[URIRef]:
    """Resolve each seed string to a URI using label index first, then comment-embedding cosine.

    Seeds with no label hit fall through to the embedding fallback.
    If multiple seeds need fallback, embeddings are computed in one batched call
    (seeds first, then all comment values) for efficiency.
    """
    resolved: set[URIRef] = set()
    unresolved: list[str] = []

    for seed in seeds:
        key = seed.strip().lower()
        if key in label_index:
            resolved.add(label_index[key])
        else:
            unresolved.append(seed)

    if unresolved and comment_index:
        comment_uris = list(comment_index.keys())
        comment_texts = [comment_index[u] for u in comment_uris]
        all_vecs = embed_caller(unresolved + comment_texts)
        if len(all_vecs) == len(unresolved) + len(comment_texts):
            seed_vecs = all_vecs[: len(unresolved)]
            comment_vecs = all_vecs[len(unresolved):]
            for seed_vec in seed_vecs:
                best_uri = None
                best_sim = similarity_threshold
                for uri, cvec in zip(comment_uris, comment_vecs):
                    sim = _cosine(seed_vec, cvec)
                    if sim > best_sim:
                        best_sim = sim
                        best_uri = uri
                if best_uri is not None:
                    resolved.add(best_uri)

    return resolved


KNOWN_PREFIXES: list[tuple[str, str]] = [
    ("evsla", "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"),
    ("icm", "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"),
    ("imo", "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/"),
    ("met", "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/"),
    ("quan", "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/"),
    ("fun", "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("skos", "http://www.w3.org/2004/02/skos/core#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


def _shorten(node: Node) -> str:
    s = str(node)
    for prefix, ns in KNOWN_PREFIXES:
        if s.startswith(ns):
            return f"{prefix}:{s[len(ns):]}"
    return f"<{s}>"


def serialize_subgraph(
    triples: list[tuple[Node, Node, Node]],
    comment_index: dict[URIRef, str],
) -> str:
    """Render triples as `s p o` lines plus a comment block for URIs in `comment_index`."""
    triple_lines = [f"{_shorten(s)} {_shorten(p)} {_shorten(o)}" for s, p, o in triples]
    uris_in_subgraph: set[URIRef] = set()
    for s, _, o in triples:
        if isinstance(s, URIRef):
            uris_in_subgraph.add(s)
        if isinstance(o, URIRef):
            uris_in_subgraph.add(o)
    comment_lines: list[str] = []
    for uri in sorted(uris_in_subgraph, key=str):
        if uri in comment_index:
            comment_lines.append(f"# comment: {_shorten(uri)} -> {comment_index[uri]}")
    parts = ["# triples"] + triple_lines
    if comment_lines:
        parts.append("")
        parts.append("# comments")
        parts.extend(comment_lines)
    return "\n".join(parts)
